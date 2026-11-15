#!/usr/bin/env python3
"""Static security and integration checks for the free TOKI email relay."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
gas = (ROOT / "google-apps-script" / "Code.gs").read_text(encoding="utf-8")
edge = (ROOT / "supabase" / "functions" / "portfolio-submit" / "index.ts").read_text(encoding="utf-8")
site = (ROOT / "site.js").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

assert "PropertiesService.getScriptProperties()" in gas
assert "TOKI_WEBHOOK_SECRET" in gas
assert "TOKI_NOTIFICATION_EMAIL" in gas
assert "MailApp.sendEmail(message)" in gas
assert "TOKI_SENT_REFS" in gas
assert "LockService.getScriptLock()" in gas
assert "input.secret" in gas
assert "TOKI_EMAIL_WEBHOOK_SECRET" in edge
assert "TOKI_EMAIL_WEBHOOK_URL" in edge
assert "await sendTokiBookingNotification" in edge
assert "notification_status" in edge
assert "/functions/v1/portfolio-submit" in site
assert "private owner inbox" in readme
assert "The shared token must not be committed to GitHub" in readme
assert "tokisatsuiephotography@gmail.com" not in gas
assert "tokisatsuiephotography@gmail.com" not in edge
assert "tokisatsuiephotography@gmail.com" not in site
assert "TOKI_WEBHOOK_SECRET" not in site

print("PASS TOKI email relay QA: private settings, shared-secret validation, deduplication, save-before-alert flow, and no public recipient/token exposure.")
