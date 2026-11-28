#!/usr/bin/env python3
"""Static contract checks for TOKI's public API limits and retry semantics."""
from pathlib import Path
import re

source = Path("supabase/functions/toki-calendar/index.ts").read_text(encoding="utf-8")
assert "const CALENDAR_LIMIT = 30;" in source
assert "const CALENDAR_WINDOW_SECONDS = 600;" in source
assert 'p_scope: "toki_calendar"' in source
assert "p_limit: CALENDAR_LIMIT" in source
assert '{ "Retry-After": String(CALENDAR_WINDOW_SECONDS) }' in source
assert '"Access-Control-Allow-Methods": "GET, OPTIONS"' in source
assert 'if (!isAllowedOrigin(origin))' in source
assert '"Cache-Control": "no-store, private"' in source
assert '"X-Content-Type-Options": "nosniff"' in source
assert '"X-Frame-Options": "DENY"' in source
assert '"Referrer-Policy": "no-referrer"' in source
assert 'PORTFOLIO_ADDITIONAL_ALLOWED_ORIGINS' in source
assert re.search(r'["\']https://toki-satsuei\.pages\.dev["\']', source)
assert 'ALLOWED_ORIGINS.has(origin)' in source

booking = Path("supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
calendar = source
for label, text in (("booking", booking), ("calendar", calendar)):
    assert "function trustedClientAddress(request: Request)" in text, f"{label}: trusted IP resolver missing"
    assert "function trustedClientAddress(request: Request): string | null" in text, f"{label}: trusted IP resolver must have nullable return type"
    assert "cf-connecting-ip" in text, f"{label}: Cloudflare client IP header missing"
    assert "x-forwarded-for" not in text and "x-real-ip" not in text, f"{label}: untrusted proxy header accepted"
assert booking.index("consumeQuota(bucket, 'portfolio_turnstile_verify', 20)") < booking.index("verifyTurnstile(token, expectedAction, secret, isTokiBooking, hostnameForOrigin(origin))"), "a dedicated verification quota must protect the CAPTCHA provider"
assert 'PORTFOLIO_ADDITIONAL_ALLOWED_ORIGINS' in booking
assert re.search(r'["\']https://toki-satsuei\.pages\.dev["\']', booking)
assert 'ALLOWED_ORIGINS.has(origin)' in booking
assert booking.index("verifyTurnstile(token, expectedAction, secret, isTokiBooking, hostnameForOrigin(origin))") < booking.index("consumeQuota(bucket, kind, limits[kind] ?? 4)"), "normal submission quota must be charged only after successful human verification"
assert "payload.hostname === expectedHostname" in booking, "Turnstile hostname must match the exact allowlisted request origin"
assert "return null;" in booking and "if (!forwarded)" in booking, "missing trusted client IP must fail closed rather than sharing one fallback quota bucket"

print("PASS TOKI API security contract: trusted client IP, pre-verification quota, post-verification submission quota, quota, retry window, CORS, cache, and response hardening.")
