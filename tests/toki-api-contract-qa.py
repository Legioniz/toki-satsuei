#!/usr/bin/env python3
"""Static contract checks for TOKI's public API limits and retry semantics."""
from pathlib import Path

source = Path("supabase/functions/toki-calendar/index.ts").read_text(encoding="utf-8")
assert "const CALENDAR_LIMIT = 30;" in source
assert "const CALENDAR_WINDOW_SECONDS = 600;" in source
assert 'p_scope: "toki_calendar"' in source
assert "p_limit: CALENDAR_LIMIT" in source
assert '{ "Retry-After": String(CALENDAR_WINDOW_SECONDS) }' in source
assert '"Access-Control-Allow-Methods": "GET, OPTIONS"' in source
assert 'origin !== ALLOWED_ORIGIN' in source
assert '"Cache-Control": "no-store, private"' in source
assert '"X-Content-Type-Options": "nosniff"' in source
assert '"X-Frame-Options": "DENY"' in source
assert '"Referrer-Policy": "no-referrer"' in source

booking = Path("supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
calendar = source
for label, text in (("booking", booking), ("calendar", calendar)):
    assert "function trustedClientAddress(request: Request)" in text, f"{label}: trusted IP resolver missing"
    assert "cf-connecting-ip" in text, f"{label}: Cloudflare client IP header missing"
    assert "x-forwarded-for" not in text and "x-real-ip" not in text, f"{label}: untrusted proxy header accepted"
assert booking.index("verifyTurnstile(token, expectedAction, secret, isTokiBooking)") < booking.index("const forwarded = trustedClientAddress(request)"), "booking quota must not be consumed before human verification"

print("PASS TOKI API security contract: trusted client IP, Turnstile-before-quota, quota, retry window, CORS, cache, and response hardening.")
