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
print("PASS TOKI API security contract: quota, retry window, CORS, cache, and response hardening.")
