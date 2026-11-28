#!/usr/bin/env python3
"""Live HTTP security checks for the public TOKI Supabase endpoints."""
from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

_SITE_CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "site-config.json").read_text(encoding="utf-8")
)

SUPABASE = _SITE_CONFIG["supabase_url"]
INTAKE = SUPABASE + "/functions/v1/portfolio-submit"
CALENDAR = SUPABASE + "/functions/v1/toki-calendar"
REST = SUPABASE + "/rest/v1"
PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS"
ALLOWED_ORIGIN = os.getenv("TOKI_ALLOWED_ORIGIN", _SITE_CONFIG["canonical_origin"]).strip()
PAGES_ORIGIN = os.getenv("TOKI_MIRROR_ORIGIN", _SITE_CONFIG["mirror_origin"]).strip()
UNTRUSTED_ORIGIN = "https://untrusted.example"
EXPECT_TURNSTILE = os.getenv("TOKI_EXPECT_TURNSTILE", "0").strip().lower() in {"1", "true", "yes"}


def request(url: str, method: str = "GET", origin: str | None = ALLOWED_ORIGIN,
            payload: object | None = None, raw: bytes | None = None,
            extra_headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    headers = {"apikey": PUBLISHABLE_KEY, "Cache-Control": "no-store"}
    if origin is not None:
        headers["Origin"] = origin
    if payload is not None:
        headers["Content-Type"] = "application/json"
        raw = json.dumps(payload).encode("utf-8")
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, data=raw, headers=headers, method=method)
    for attempt in range(2):
        try:
            with urlopen(req, timeout=20) as response:
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as error:
            return error.code, dict(error.headers.items()), error.read()
        except (TimeoutError, socket.timeout) as error:
            if attempt == 0:
                time.sleep(1)
                continue
            raise AssertionError(f"Live endpoint timed out after one retry: {url}") from error
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)) and attempt == 0:
                time.sleep(1)
                continue
            raise AssertionError(f"Live endpoint unavailable: {error.reason}") from error
    raise AssertionError(f"Live endpoint request did not complete: {url}")


def decode(body: bytes) -> dict:
    try:
        value = json.loads(body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AssertionError("Endpoint did not return valid JSON") from error
    assert isinstance(value, dict), "Expected JSON object response"
    return value


def main() -> None:
    # Public readiness exposes no credential material.
    status, _, body = request(INTAKE, "GET")
    assert status == 200, f"Intake health probe returned {status}: {body[:300]!r}"
    health = decode(body)
    assert health.get("ok") is True and health.get("service") == "portfolio-submit"
    assert "secret" not in body.decode("utf-8").lower()

    # CORS allows the published site, but never reflects an arbitrary origin.
    status, headers, _ = request(INTAKE, "OPTIONS", ALLOWED_ORIGIN,
                                 extra_headers={"Access-Control-Request-Method": "POST",
                                                "Access-Control-Request-Headers": "apikey,content-type"})
    assert status == 204, f"Allowed CORS preflight returned {status}"
    assert headers.get("Access-Control-Allow-Origin") == ALLOWED_ORIGIN

    # The replacement Pages origin is explicitly allowlisted on both public APIs.
    status, headers, _ = request(INTAKE, "OPTIONS", PAGES_ORIGIN,
                                 extra_headers={"Access-Control-Request-Method": "POST",
                                                "Access-Control-Request-Headers": "apikey,content-type"})
    assert status == 204 and headers.get("Access-Control-Allow-Origin") == PAGES_ORIGIN
    status, headers, _ = request(CALENDAR, "OPTIONS", PAGES_ORIGIN,
                                 extra_headers={"Access-Control-Request-Method": "GET",
                                                "Access-Control-Request-Headers": "apikey,content-type"})
    assert status == 204 and headers.get("Access-Control-Allow-Origin") == PAGES_ORIGIN

    status, _, body = request(INTAKE, "POST", PAGES_ORIGIN, {"kind": "toki_booking", "website": ""})
    assert status == 400, f"Pages origin was not accepted by the booking intake: {status} {body[:200]!r}"

    status, headers, _ = request(INTAKE, "OPTIONS", UNTRUSTED_ORIGIN,
                                 extra_headers={"Access-Control-Request-Method": "POST"})
    assert status == 204
    assert headers.get("Access-Control-Allow-Origin") != UNTRUSTED_ORIGIN
    status, _, body = request(INTAKE, "POST", UNTRUSTED_ORIGIN, {"kind": "toki_booking"})
    assert status == 403, f"Untrusted Origin POST was not rejected: {status} {body[:200]!r}"

    # Method, origin, malformed JSON, unsupported kinds, and body-size limits.
    status, _, _ = request(INTAKE, "PUT", ALLOWED_ORIGIN, {"kind": "toki_booking"})
    assert status == 405, f"Unsupported HTTP method returned {status}"
    status, _, _ = request(INTAKE, "POST", None, {"kind": "toki_booking"})
    assert status == 403, f"Origin-less POST returned {status}"
    status, _, _ = request(INTAKE, "POST", ALLOWED_ORIGIN, raw=b"{", extra_headers={"Content-Type": "application/json"})
    assert status == 400, f"Malformed JSON returned {status}"
    status, _, _ = request(INTAKE, "POST", ALLOWED_ORIGIN, raw=b"{}", extra_headers={"Content-Type": "text/plain"})
    assert status == 415, f"Unsupported content type returned {status}"
    status, _, _ = request(INTAKE, "POST", ALLOWED_ORIGIN, {"kind": "not-supported"})
    assert status == 400, f"Unsupported submission type returned {status}"
    status, _, _ = request(INTAKE, "POST", ALLOWED_ORIGIN, raw=b" " * 12001,
                           extra_headers={"Content-Type": "application/json"})
    assert status == 413, f"Oversized request returned {status}"

    status, _, _ = request(REST + "/rpc/consume_portfolio_quota", "POST", ALLOWED_ORIGIN,
                           {"p_bucket_hash": "0" * 64, "p_scope": "toki_booking", "p_limit": 4})
    assert status != 200, "Anonymous caller executed the internal quota RPC"

    import secrets
    test_gallery_token = "toki-" + secrets.token_hex(32)
    gallery_attempts = []
    for _ in range(11):
        code, _, response_body = request(REST + "/rpc/toki_get_client_gallery", "POST", ALLOWED_ORIGIN, {"p_token": test_gallery_token})
        assert code == 200, f"Gallery RPC returned unexpected HTTP status {code}"
        gallery_attempts.append(decode(response_body))
    assert all(item.get("ok") is False and item.get("code") != "rate_limited" for item in gallery_attempts), (
        "Unknown random gallery keys must not consume the shared or per-token quota"
    )

    # Anonymous callers must not read the private booking table or inbox.
    for resource in ("toki_booking_requests", "toki_booking_inbox"):
        status, _, body = request(REST + "/" + resource + "?select=reference_code", "GET", ALLOWED_ORIGIN)
        assert status != 200, f"Anonymous access unexpectedly read {resource}: {body[:200]!r}"

    # The public calendar is intentionally public, but returns only its three approved fields.
    month = datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y-%m")
    status, _, body = request(CALENDAR + "?month=" + month, "GET", ALLOWED_ORIGIN)
    assert status == 200, f"Public calendar returned {status}: {body[:300]!r}"
    # The same confirmed-time projection must remain available from the new Pages origin.
    pages_status, _, pages_body = request(CALENDAR + "?month=" + month, "GET", PAGES_ORIGIN)
    assert pages_status == 200, f"Pages-origin calendar returned {pages_status}: {pages_body[:300]!r}"
    pages_calendar = decode(pages_body)
    assert pages_calendar.get("ok") is True and isinstance(pages_calendar.get("bookings"), list)
    calendar = decode(body)
    assert calendar.get("ok") is True and isinstance(calendar.get("bookings"), list)
    for booking in calendar["bookings"]:
        assert set(booking) == {"date", "start_time", "end_time"}, "Calendar exposed unexpected booking fields"

    # Missing/invalid Turnstile tokens must be rejected before the booking quota is charged.
    # This prevents unauthenticated probes from exhausting a real visitor's booking allowance.
    booking_responses = []
    for _ in range(5):
        code, _, response_body = request(INTAKE, "POST", ALLOWED_ORIGIN,
                                         {"kind": "toki_booking", "website": ""})
        booking_responses.append((code, decode(response_body)))
    assert all(code == 400 for code, _ in booking_responses), (
        "Invalid Turnstile probes must be rejected without consuming the booking quota: "
        + repr([code for code, _ in booking_responses])
    )
    if EXPECT_TURNSTILE:
        assert all("human verification failed" in payload.get("message", "").lower()
                   for _, payload in booking_responses), (
            "Missing tokens are not being rejected by live Turnstile verification: "
            + repr([payload for _, payload in booking_responses])
        )

        # A non-empty malformed token must reach Cloudflare Siteverify. This
        # distinguishes a real server-side provider call from the early
        # missing-token rejection above. It must fail closed and never create
        # a booking or consume the normal booking quota.
        status, _, body = request(
            INTAKE,
            "POST",
            ALLOWED_ORIGIN,
            {"kind": "toki_booking", "website": "", "turnstileToken": "toki-invalid-siteverify-smoke-token"},
        )
        payload = decode(body)
        assert status == 400 and "human verification failed" in payload.get("message", "").lower(), (
            "A malformed non-empty token did not fail closed through the Siteverify path: "
            + repr({"status": status, "payload": payload})
        )

    print("PASS live TOKI HTTP security QA: CORS, origin and method restrictions, invalid/oversized payloads, private REST authorization, gallery quota isolation, calendar field minimization, missing-token rejection, and non-empty-token Siteverify smoke path.")


if __name__ == "__main__":
    main()
