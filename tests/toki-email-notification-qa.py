#!/usr/bin/env python3
"""Static security and integration checks for the TOKI Make.com notification webhook."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
edge = (ROOT / "supabase" / "functions" / "portfolio-submit" / "index.ts").read_text(encoding="utf-8")
site = (ROOT / "site.js").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
policy = (ROOT / "policies.html").read_text(encoding="utf-8")

# The private server-side integration sends booking details only after Supabase saves them.
assert "TOKI_EMAIL_WEBHOOK_URL" in edge
assert "TOKI_EMAIL_WEBHOOK_API_KEY" in edge
assert "await sendTokiBookingNotification" in edge
assert "notification_status" in edge
assert "kind: 'toki_booking_notification'" in edge
assert "x-make-apikey" in edge
assert "The request was saved but its reference could not be confirmed." in edge
assert "Make's default Custom Webhook response" in edge
assert "queued" in edge and "not_configured" in edge and "failed" in edge

# The browser posts to the protected intake function and never receives webhook secrets.
assert "/functions/v1/portfolio-submit" in site
assert 'kind:"toki_booking"' in site
assert "TOKI_EMAIL_WEBHOOK_URL" not in site
assert "TOKI_EMAIL_WEBHOOK_API_KEY" not in site
assert "tokisatsuiephotography@gmail.com" not in edge
assert "tokisatsuiephotography@gmail.com" not in site

# Current public documentation must accurately describe the Make.com workflow.
assert "private owner inbox" in readme
assert "Make.com Custom Webhook" in readme
assert "Never put the webhook URL or API key" in readme
assert "Make.com automation webhook" in policy
assert "webhook credentials are not published on the website" in policy
assert "not a booking confirmation" in policy

print("PASS TOKI notification QA: private Make.com webhook settings, server-only API key, save-before-alert flow, queue semantics, and no public secret exposure.")
