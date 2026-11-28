#!/usr/bin/env python3
"""Verify the official GitHub Pages content and the Cloudflare mirror response-header contract."""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen

_SITE_CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "site-config.json").read_text(encoding="utf-8")
)

DEFAULT_SITE_URL = _SITE_CONFIG["canonical_base_url"]
SITE_URL = os.getenv("TOKI_SITE_URL", DEFAULT_SITE_URL).strip()
REQUIRE_HEADERS = os.getenv("TOKI_REQUIRE_SECURITY_HEADERS", "1").strip().lower() in {
    "1", "true", "yes",
}
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_CANONICAL_PARTS = urlsplit(DEFAULT_SITE_URL)
GITHUB_PAGES_HOST = _CANONICAL_PARTS.netloc
GITHUB_PAGES_PATH = _CANONICAL_PARTS.path.rstrip("/")



class PageAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []
        self.resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            rel = (values.get("rel") or "").lower()
            if "stylesheet" in rel:
                self.stylesheets.append(values["href"])
            elif "icon" in rel or "manifest" in rel:
                self.resources.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag in {"img", "source", "video", "audio"}:
            if values.get("src"):
                self.resources.append(values["src"])
            if values.get("poster"):
                self.resources.append(values["poster"])
            srcset = values.get("srcset")
            if srcset:
                self.resources.extend(
                    candidate.strip().split()[0]
                    for candidate in srcset.split(",")
                    if candidate.strip()
                )


RETRYABLE_HTTP_STATUSES = frozenset({404, 429, 500, 502, 503, 504})
MAX_FETCH_ATTEMPTS = 8


def retry_delay(attempt: int) -> int:
    """Bounded backoff for Pages CDN alias propagation immediately after deploy."""
    return min(2 * (attempt + 1), 10)


def fetch(url: str) -> tuple[int, str, dict[str, str], bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": "TOKI-SATSU-EI-Live-Security-QA/1.0",
            "Cache-Control": "no-cache",
            "Accept-Encoding": "identity",
        },
    )
    last_error: Exception | None = None
    for attempt in range(MAX_FETCH_ATTEMPTS):
        try:
            with urlopen(request, timeout=25) as response:
                return (
                    response.status,
                    response.geturl(),
                    {key.lower(): value for key, value in response.headers.items()},
                    response.read(),
                )
        except HTTPError as error:
            if error.code in RETRYABLE_HTTP_STATUSES and attempt < MAX_FETCH_ATTEMPTS - 1:
                delay = retry_delay(attempt)
                print(
                    f"Retrying transient HTTP {error.code} for {error.geturl()} "
                    f"after {delay}s (attempt {attempt + 1}/{MAX_FETCH_ATTEMPTS})."
                )
                error.close()
                time.sleep(delay)
                continue
            return (
                error.code,
                error.geturl(),
                {key.lower(): value for key, value in error.headers.items()},
                error.read(),
            )
        except (URLError, TimeoutError, socket.timeout) as error:
            last_error = error
            if attempt == MAX_FETCH_ATTEMPTS - 1:
                break
            delay = retry_delay(attempt)
            print(
                f"Retrying live site request after network error: {error} "
                f"({delay}s; attempt {attempt + 1}/{MAX_FETCH_ATTEMPTS})."
            )
            time.sleep(delay)
    raise AssertionError(
        f"Live site request failed after {MAX_FETCH_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def missing_security_headers(headers: dict[str, str]) -> list[str]:
    checks = {
        "strict-transport-security": lambda value: bool(
            re.search(r"(?:^|;)\s*max-age=31536000(?:;|$)", value, re.I)
        ),
        "x-frame-options": lambda value: value.strip().lower() in {"sameorigin", "deny"},
        "x-content-type-options": lambda value: value.strip().lower() == "nosniff",
        "referrer-policy": lambda value: value.strip().lower() == "strict-origin-when-cross-origin",
        "permissions-policy": lambda value: all(
            token in value.lower()
            for token in ("camera=()", "microphone=()", "geolocation=()")
        ),
        "content-security-policy": lambda value: (
            all(
                token in value.lower()
                for token in (
                    "default-src 'self'",
                    "object-src 'none'",
                    "frame-ancestors 'self'",
                    "base-uri 'self'",
                )
            )
            and not re.search(
                r"(?:^|;)\s*script-src[^;]*'unsafe-(?:inline|eval)'",
                value,
                re.IGNORECASE,
            )
        ),
    }
    return [
        name for name, validate in checks.items()
        if name not in headers or not validate(headers[name])
    ]


def cache_policy_error(headers: dict[str, str], *, private: bool) -> str | None:
    value = headers.get("cache-control", "").lower()
    if private:
        return None if "no-store" in value else "private-html-cache-control"
    if not any(token in value for token in ("no-cache", "no-store", "max-age=0")):
        return "html-cache-control"
    if "no-store" not in value and "must-revalidate" not in value:
        return "html-cache-revalidation"
    return None


def verify_live_site() -> None:
    if not SITE_URL or urlsplit(SITE_URL).scheme != "https":
        raise SystemExit("TOKI_SITE_URL must be a non-empty HTTPS URL")
    base = SITE_URL if SITE_URL.endswith("/") else SITE_URL + "/"
    parsed_base = urlsplit(base)
    origin = parsed_base.netloc
    github_pages = (
        parsed_base.hostname == GITHUB_PAGES_HOST
        and parsed_base.path.rstrip("/") == GITHUB_PAGES_PATH
    )
    if parsed_base.hostname == GITHUB_PAGES_HOST and not github_pages:
        raise SystemExit(
            f"GitHub Pages verification must use https://{GITHUB_PAGES_HOST}{GITHUB_PAGES_PATH}/"
        )
    problems: list[str] = []

    routes = (
        ("", False),
        ("booking.html", False),
        ("library.html", False),
        ("policies.html", False),
        ("admin.html", True),
        ("client-gallery.html", True),
        ("404.html", False),
    )
    home_url = base
    home_body = b""
    for route, private in routes:
        status, final_url, headers, body = fetch(urljoin(base, route))
        if not 200 <= status < 300:
            raise AssertionError(f"Live route {route or '/'} returned HTTP {status}: {final_url}")
        if urlsplit(final_url).netloc != origin:
            raise AssertionError(f"Unexpected host redirect for {route or '/'}: {final_url}")
        body_lower = body.lower()
        required_meta_csp = (
            b'<meta http-equiv="content-security-policy"' in body_lower
            and b"default-src 'self'" in body_lower
            and b"object-src 'none'" in body_lower
            and b"base-uri 'self'" in body_lower
            and b"form-action 'self'" in body_lower
            and b"script-src" in body_lower
            and b'<meta name="referrer" content="strict-origin-when-cross-origin">' in body_lower
        )
        if not required_meta_csp:
            problems.append(f"{route or '/'}:csp-meta-fallback")

        # GitHub Pages is the canonical public address, but it does not support
        # per-path response headers or Cache-Control rules from a repository
        # _headers file. Verify its HTML CSP fallback and content fingerprints;
        # enforce the complete response-header contract on the Cloudflare mirror.
        if not github_pages:
            for name in missing_security_headers(headers):
                problems.append(f"{route or '/'}:{name}")
            cache_error = cache_policy_error(headers, private=private)
            if cache_error:
                problems.append(f"{route or '/'}:{cache_error}")
        if not route:
            home_url, home_body = final_url, body

    parser = PageAssets()
    parser.feed(home_body.decode("utf-8", errors="replace"))
    local_assets: list[str] = []
    for value in parser.stylesheets + parser.scripts + parser.resources:
        asset_url = urljoin(home_url, value)
        if urlsplit(asset_url).netloc == origin:
            local_assets.append(asset_url)
    if not parser.stylesheets or not parser.scripts:
        raise AssertionError("Live home page did not expose both CSS and JavaScript dependencies")

    checked_assets: list[str] = []
    for asset_url in dict.fromkeys(local_assets):
        parsed = urlsplit(asset_url)
        versions = parse_qs(parsed.query).get("v", [])
        if len(versions) != 1 or not FINGERPRINT_PATTERN.fullmatch(versions[0]):
            raise AssertionError(f"Local asset URL lacks a 128-bit SHA-256 fingerprint: {asset_url}")

        status, final_url, headers, payload = fetch(asset_url)
        if not 200 <= status < 300:
            raise AssertionError(f"Fingerprint asset returned HTTP {status}: {asset_url}")
        actual = hashlib.sha256(payload).hexdigest()[:32]
        if actual != versions[0]:
            raise AssertionError(
                f"Fingerprint mismatch for {asset_url}: URL={versions[0]}, response={actual}"
            )
        if not github_pages:
            cache = headers.get("cache-control", "").lower()
            if "immutable" not in cache or "max-age=31536000" not in cache:
                problems.append(f"{parsed.path}:immutable-cache-control")
        checked_assets.append(parsed.path)

    problems = sorted(set(problems))
    if problems:
        message = (
            f"Live host {origin} is missing or misconfigures: " + ", ".join(problems)
        )
        if REQUIRE_HEADERS:
            raise AssertionError(message)
        print("WARN " + message)
        print(
            "Live response headers or cache directives failed validation. "
            "The production verifier must run against the Cloudflare Pages origin "
            "with TOKI_REQUIRE_SECURITY_HEADERS=1."
        )

    print(
        f"PASS live TOKI asset verification: {home_url}; "
        f"{len(checked_assets)} local CSS/JS/media assets fetched and matched to their SHA-256 URLs."
    )
    if github_pages:
        print(
            "PASS official GitHub Pages verification: all seven routes include the CSP meta "
            "fallback and every same-origin asset matches its SHA-256 URL."
        )
        print(
            "LIMITATION: GitHub Pages does not apply repository _headers files or allow "
            "per-route response-header/cache configuration. The Cloudflare Pages mirror "
            "is separately checked for the complete HSTS/CSP/X-Frame-Options/"
            "X-Content-Type-Options/Referrer-Policy/Permissions-Policy/cache contract."
        )
    elif not problems:
        print(
            "PASS Cloudflare Pages HTTP security: HSTS, response CSP with frame-ancestors, "
            "framing, MIME, referrer, permissions, HTML revalidation, private no-store, "
            "and immutable assets."
        )


def main() -> None:
    """Retry a complete live snapshot when Pages edges briefly serve mixed revisions."""
    attempts = 6
    delay_seconds = 5
    for attempt in range(1, attempts + 1):
        try:
            verify_live_site()
            return
        except AssertionError as error:
            # A stale HTML document can briefly reference the previous fingerprint
            # while the same deployment edge is already serving the replacement
            # asset at that stable path. Refetch every page and asset together so
            # the verifier validates one coherent snapshot, not mixed revisions.
            if "Fingerprint mismatch" not in str(error):
                raise
            if attempt == attempts:
                raise AssertionError(
                    f"Live Pages content did not converge after {attempts} complete "
                    f"verification attempts: {error}"
                ) from error
            print(
                f"WARN transient Pages fingerprint mismatch on snapshot "
                f"{attempt}/{attempts}; refetching all routes and assets in "
                f"{delay_seconds}s: {error}"
            )
            time.sleep(delay_seconds)


if __name__ == "__main__":
    main()
