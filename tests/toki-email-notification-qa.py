#!/usr/bin/env python3
"""Static security and integration checks for the TOKI Make.com notification webhook."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
edge = (ROOT / "supabase" / "functions" / "portfolio-submit" / "index.ts").read_text(encoding="utf-8")
site = (ROOT / "src" / "js" / "site.js").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
policy = (ROOT / "policies.html").read_text(encoding="utf-8")

# The private server-side integration sends booking details only after Supabase saves them.
assert "TOKI_EMAIL_WEBHOOK_URL" in edge
assert "TOKI_EMAIL_WEBHOOK_API_KEY" in edge
assert "await sendTokiBookingNotification" in edge
assert "notification_status" in edge
assert "kind: 'toki_booking_notification'" in edge
assert "booking_terms_accepted_at" in edge
assert "booking_terms_version" in edge
assert "bookingTermsConsent" in edge
assert "booking_terms_consent" in site
assert "x-make-apikey" in edge
assert "The request was saved but its reference could not be confirmed." in edge
assert "Make's default Custom Webhook response" in edge
assert "queued" in edge and "not_configured" in edge and "failed" in edge

# The browser posts to the protected intake function and never receives webhook secrets.
assert "/functions/v1/portfolio-submit" in site
assert 'kind:"toki_booking"' in site
assert "TOKI_EMAIL_WEBHOOK_URL" not in site
assert "TOKI_EMAIL_WEBHOOK_API_KEY" not in site
email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
assert email_pattern.search(edge) is None
assert email_pattern.search(site) is None

# Current public documentation must accurately describe the Make.com workflow.
assert "Booking administration is handled directly in the Supabase Dashboard" in readme
assert "private Make Custom Webhook" in readme
assert "There is no Google Sheets synchronization" in readme
assert "Never put webhook URLs, API keys" in readme
assert "private Supabase booking table" in policy
assert "Supabase is the only record we use to track booking requests and their status" in policy
assert "Cloudflare Turnstile" in policy
assert "webhook credentials are not published on the website" not in policy
assert "not a booking confirmation" in policy

print("PASS TOKI notification QA: private Make.com webhook settings, server-only API key, save-before-alert flow, queue semantics, and no public secret exposure.")
