#!/usr/bin/env python3
"""Verify deployed TOKI security response headers and content-addressed asset URLs."""
from __future__ import annotations

import hashlib
import os
import re
import socket
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, urlopen

DEFAULT_SITE_URL = "https://legioniz.github.io/toki-satsuei/"
SITE_URL = os.getenv("TOKI_SITE_URL", DEFAULT_SITE_URL).strip()
REQUIRE_HEADERS = os.getenv("TOKI_REQUIRE_SECURITY_HEADERS", "0").strip().lower() in {
    "1", "true", "yes",
}
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class PageAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower():
            if values.get("href"):
                self.stylesheets.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])


def fetch(url: str) -> tuple[int, str, dict[str, str], bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": "TOKI-SATSU-EI-Live-Security-QA/1.0",
            "Cache-Control": "no-cache",
            "Accept-Encoding": "identity",
        },
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                return (
                    response.status,
                    response.geturl(),
                    {key.lower(): value for key, value in response.headers.items()},
                    response.read(),
                )
        except HTTPError as error:
            return (
                error.code,
                error.geturl(),
                {key.lower(): value for key, value in error.headers.items()},
                error.read(),
            )
        except (URLError, TimeoutError, socket.timeout) as error:
            if attempt == 2:
                raise AssertionError(f"Live site request failed after retries: {error}") from error
            time.sleep(2)
    raise AssertionError("Live site request did not complete")


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
        "content-security-policy": lambda value: all(
            token in value.lower()
            for token in (
                "default-src 'self'",
                "object-src 'none'",
                "frame-ancestors 'self'",
                "base-uri 'self'",
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


def main() -> None:
    if not SITE_URL or urlsplit(SITE_URL).scheme != "https":
        raise SystemExit("TOKI_SITE_URL must be a non-empty HTTPS URL")
    base = SITE_URL if SITE_URL.endswith("/") else SITE_URL + "/"
    origin = urlsplit(base).netloc
    problems: list[str] = []
    all_html_headers: list[tuple[str, dict[str, str]]] = []

    routes = (
        ("", False),
        ("booking.html", False),
        ("library.html", False),
        ("policies.html", False),
        ("admin.html", True),
        ("client-gallery.html", True),
    )
    home_status = 0
    home_url = base
    home_body = b""
    for route, private in routes:
        status, final_url, headers, body = fetch(urljoin(base, route))
        if not 200 <= status < 300:
            raise AssertionError(f"Live route {route or '/'} returned HTTP {status}: {final_url}")
        if urlsplit(final_url).netloc != origin:
            raise AssertionError(f"Unexpected host redirect for {route or '/'}: {final_url}")
        all_html_headers.append((route or "/", headers))
        for name in missing_security_headers(headers):
            problems.append(f"{route or '/'}:{name}")
        cache_error = cache_policy_error(headers, private=private)
        if cache_error:
            problems.append(f"{route or '/'}:{cache_error}")
        if not route:
            home_status, home_url, home_body = status, final_url, body

    parser = PageAssets()
    parser.feed(home_body.decode("utf-8", errors="replace"))
    local_assets: list[str] = []
    for value in parser.stylesheets + parser.scripts:
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
            "The current GitHub Pages origin does not apply repository _headers rules. "
            "Switch to a header-capable origin, set TOKI_SITE_URL to that HTTPS URL, "
            "and enable TOKI_REQUIRE_SECURITY_HEADERS=1 to make header failures blocking."
        )

    print(
        f"PASS live TOKI asset verification: {home_url}; "
        f"{len(checked_assets)} local CSS/JS assets fetched and matched to their SHA-256 URLs."
    )
    if not problems:
        print(
            "PASS live TOKI HTTP security: HSTS, CSP, framing, MIME, referrer, "
            "permissions, HTML revalidation, private no-store, and immutable assets."
        )


if __name__ == "__main__":
    main()
