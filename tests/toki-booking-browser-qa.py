#!/usr/bin/env python3
"""Browser QA for the Supabase-backed TOKI SATSUEI booking request form."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUPABASE_HOST = "https://pjuwrngnrrvdiwqspkic.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def fill_valid_form(page) -> tuple[str, str]:
    today = datetime.now(ZoneInfo("Asia/Manila")).date()
    preferred_date = (today + timedelta(days=20)).isoformat()
    alternate_date = (today + timedelta(days=21)).isoformat()
    page.locator('input[name="name"]').fill("Alex Cosplayer")
    page.locator('select[name="session"]').select_option("Duo Session")
    page.locator('input[name="preferred_date"]').fill(preferred_date)
    page.locator('input[name="alternate_date"]').fill(alternate_date)
    page.locator('input[name="preferred_time"]').fill("14:30")
    page.locator('select[name="contact_method"]').select_option("instagram")
    page.locator('input[name="contact_value"]').fill("@alex.cosplay")
    page.locator('input[name="participants"]').fill("2")
    page.locator('input[name="location"]').fill("Quezon City")
    page.locator('textarea[name="notes"]').fill("Duo cosplay session for two characters. We can meet near the venue entrance.")
    page.locator('input[name="privacy_consent"]').check()
    page.locator('input[name="booking_terms_consent"]').check()
    return preferred_date, alternate_date


def main() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    site = (ROOT / "site.js").read_text(encoding="utf-8")
    edge = (ROOT / "supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
    policies = (ROOT / "policies.html").read_text(encoding="utf-8")
    assert 'id="inquiry-form"' in index
    assert 'name="privacy_consent"' in index
    assert 'name="booking_terms_consent"' in index
    assert 'data-booking-terms-version="2026-11-16-v1"' in index
    assert 'name="website"' in index
    assert 'type="time" name="preferred_time"' in index
    assert '24-hour format' in index
    assert "Copy inquiry message" not in index
    assert "TOKI_BOOKING_ENDPOINT" in site
    assert "kind:\"toki_booking\"" in site
    assert "preferredTimePattern" in edge and "preferred_time: preferredTime" in edge
    assert "bookingTermsConsent" in edge
    assert "bookingTermsVersion === expectedBookingTermsVersion" in edge
    assert "booking_terms_accepted_at: bookingTermsAcceptedAt" in edge
    assert "booking_terms_version: expectedBookingTermsVersion" in edge
    assert "booking_terms_consent" in site and "booking_terms_version" in site
    assert "function manilaNow()" in edge
    assert "(preferredDate !== now.date || preferredTime > now.time)" in edge
    assert "function manilaNow()" in site and "preferredTime.min" in site
    assert "allowedTimes = ['Morning', 'Afternoon', 'Evening', 'Flexible']" not in edge
    assert "clipboard.writeText" not in site
    assert "private Supabase booking table" in policies and "does not reserve a date" in policies.lower()
    assert 'id="toki-turnstile"' in index
    assert 'data-sitekey="0x4AAAAAAGDDFcLp8PfycH-f"' in index
    assert 'src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"></script>' in index
    assert 'api.js?render=explicit" defer' not in index
    assert 'api.js?render=explicit" async' not in index
    assert 'action:"toki_booking"' in site
    assert 'size:"flexible"' in site
    assert '"error-callback":handleTurnstileError' in site
    assert '"expired-callback":()=>updateBookingStatus' in site
    assert '"timeout-callback":()=>updateBookingStatus' in site
    assert "return true" in site
    assert "turnstileToken" in site and "getResponse" in site
    assert "Human verification failed" in edge
    assert "TOKI_TURNSTILE_SECRET_KEY" in edge
    assert "TOKI Turnstile configuration" in edge
    assert "secretConfigured: Boolean(TOKI_TURNSTILE_SECRET)" in edge
    assert "TURNSTILE_SECRET_KEY" in edge
    assert "const secret = isTokiBooking ? TOKI_TURNSTILE_SECRET : TURNSTILE_SECRET" in edge
    assert "failClosedWhenUnconfigured" in edge
    assert "Turnstile verification secret is not configured" in edge
    assert "Turnstile Siteverify rejected verification" in edge
    assert "error-codes" in edge and "hostnameMatches" in edge and "actionMatches" in edge
    assert "turnstileContainer?.scrollIntoView" in site
    assert "'toki_booking'" in edge and "return false" in edge
    assert "not a reservation" in policies.lower() or "does not reserve" in policies.lower()

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            context.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
            context.add_init_script("""
                window.turnstile = {
                    ready: (callback) => callback(),
                    render: () => "test-widget-id",
                    getResponse: () => "test-turnstile-token",
                    reset: () => { window.__turnstileReset = true; }
                };
            """)
            submissions = []


            def successful_submission(route):
                request = route.request
                if request.method == "OPTIONS":
                    route.fulfill(status=204, headers={
                        "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "apikey, content-type",
                    })
                    return
                submissions.append({
                    "headers": request.headers,
                    "payload": request.post_data_json,
                })
                route.fulfill(status=200, content_type="application/json", body=json.dumps({
                    "ok": True,
                    "reference_code": "TOKI-A1B2C3D4",
                }))

            context.route(SUPABASE_HOST + "/functions/v1/portfolio-submit", successful_submission)
            page = context.new_page()
            page.goto(base + "/index.html#contact", wait_until="domcontentloaded")
            form = page.locator("#inquiry-form")

            # Same-day requests must use a time beyond the current Manila minute.
            today_key = datetime.now(ZoneInfo("Asia/Manila")).date().isoformat()
            page.locator('input[name="preferred_date"]').fill(today_key)
            page.locator('input[name="preferred_date"]').dispatch_event("change")
            time_field = page.locator('input[name="preferred_time"]')
            assert time_field.get_attribute("min"), "Same-day time minimum was not applied"
            time_field.fill("00:00")
            assert time_field.evaluate("(node) => node.validity.rangeUnderflow || node.validity.customError"), \
                "Past same-day time was not rejected in the browser"
            assert form.count() == 1
            assert form.locator('input[name="preferred_date"]').get_attribute("required") is not None
            assert form.locator('input[name="preferred_time"]').get_attribute("type") == "time"
            assert form.locator('input[name="preferred_time"]').get_attribute("step") == "60"
            assert form.locator('input[name="preferred_time"]').get_attribute("required") is not None
            assert form.locator('input[name="privacy_consent"]').get_attribute("required") is not None
            assert form.locator('input[name="booking_terms_consent"]').get_attribute("required") is not None
            assert form.locator('input[name="website"]').get_attribute("tabindex") == "-1"

            # Package cards and the structured package selector must stay in sync.
            page.locator('.package-card[data-session="Quick Snap"]').click()
            assert page.locator('select[name="session"]').input_value() == "Quick Snap"
            assert page.locator('.package-card[data-session="Quick Snap"]').get_attribute("aria-pressed") == "true"

            # Missing required fields must be blocked before a network request.
            page.locator('button[type="submit"]').click()
            assert len(submissions) == 0

            preferred_date, alternate_date = fill_valid_form(page)
            assert page.locator('input[name="contact_value"]').get_attribute("type") == "text"
            page.locator('select[name="contact_method"]').select_option("email")
            assert page.locator('input[name="contact_value"]').get_attribute("type") == "email"
            page.locator('input[name="contact_value"]').fill("alex@example.com")
            page.locator('select[name="contact_method"]').select_option("instagram")
            page.locator('input[name="contact_value"]').fill("@alex.cosplay")

            page.locator('button[type="submit"]').click()
            page.get_by_text("TOKI-A1B2C3D4").wait_for(state="visible", timeout=7000)
            assert len(submissions) == 1
            request = submissions[0]
            assert request["headers"].get("apikey") == PUBLISHABLE_KEY
            assert request["headers"].get("authorization") is None
            payload = request["payload"]
            assert payload["kind"] == "toki_booking"
            assert payload["turnstileToken"] == "test-turnstile-token"
            assert payload["name"] == "Alex Cosplayer"
            assert payload["contact_method"] == "instagram"
            assert payload["contact_value"] == "@alex.cosplay"
            assert payload["session_type"] == "Duo Session"
            assert payload["preferred_date"] == preferred_date
            assert payload["alternate_date"] == alternate_date
            assert payload["preferred_time"] == "14:30"
            assert payload["participants"] == 2
            assert payload["privacy_consent"] is True
            assert payload["booking_terms_consent"] is True
            assert payload["booking_terms_version"] == "2026-11-16-v1"
            assert page.locator('input[name="name"]').input_value() == ""
            assert "not reserved" in page.locator("#form-status").inner_text().lower()
            assert page.locator('button[type="submit"]').is_enabled()

            page.close()

            # A server-side rate-limit or validation error must preserve the
            # visitor's entries and re-enable submission.
            error_context = browser.new_context(viewport={"width": 390, "height": 844})
            error_context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            error_context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            error_context.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
            error_context.add_init_script("""
                window.turnstile = {
                    ready: (callback) => callback(),
                    render: () => "test-widget-id",
                    getResponse: () => "test-turnstile-token",
                    reset: () => { window.__turnstileReset = true; }
                };
            """)
            failure_requests = []

            def rate_limited(route):
                if route.request.method == "OPTIONS":
                    route.fulfill(status=204, headers={
                        "Access-Control-Allow-Origin": route.request.headers.get("origin", "*"),
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "apikey, content-type",
                    })
                    return
                failure_requests.append(route.request.post_data_json)
                route.fulfill(status=429, content_type="application/json", body=json.dumps({
                    "ok": False,
                    "message": "Too many submissions. Please try again later.",
                }))

            error_context.route(SUPABASE_HOST + "/functions/v1/portfolio-submit", rate_limited)
            error_page = error_context.new_page()
            error_page.goto(base + "/index.html#contact", wait_until="domcontentloaded")
            failure_preferred_date, _ = fill_valid_form(error_page)
            error_page.locator('button[type="submit"]').click()
            error_page.get_by_text("Too many submissions. Please try again later.").wait_for(state="visible", timeout=7000)
            assert len(failure_requests) == 1
            assert error_page.locator('input[name="name"]').input_value() == "Alex Cosplayer"
            assert error_page.locator('textarea[name="notes"]').input_value().startswith("Duo cosplay")
            assert error_page.locator('button[type="submit"]').is_enabled()

            # Duplicate alternate dates are invalid before the edge function
            # receives the request.
            error_page.locator('input[name="alternate_date"]').fill(failure_preferred_date)
            error_page.locator('button[type="submit"]').click()
            assert len(failure_requests) == 1

            for width in [320, 390, 680, 768, 1024, 1440]:
                error_page.set_viewport_size({"width": width, "height": 850})
                error_page.wait_for_timeout(30)
                page_width = error_page.evaluate("() => document.documentElement.scrollWidth")
                assert page_width <= width + 1, f"Form layout overflow at {width}px ({page_width}px)"

            error_context.close()

            # An unavailable or incomplete challenge must stop the browser before it posts.
            gate_context = browser.new_context(viewport={"width": 390, "height": 844})
            gate_context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            gate_context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            gate_context.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
            gate_context.add_init_script("""
                window.turnstile = {
                    ready: (callback) => callback(),
                    render: () => "test-widget-id",
                    getResponse: () => "",
                    reset: () => {}
                };
            """)
            gate_requests = []
            gate_context.route(SUPABASE_HOST + "/functions/v1/portfolio-submit", lambda route: gate_requests.append(route.request) or route.fulfill(status=500, body="unexpected request"))
            gate_page = gate_context.new_page()
            gate_page.goto(base + "/index.html#contact", wait_until="domcontentloaded")
            fill_valid_form(gate_page)
            gate_page.locator('button[type="submit"]').click()
            assert len(gate_requests) == 0
            gate_page.get_by_text("Please complete the human-verification challenge before sending your request.").wait_for(state="visible", timeout=3000)
            assert "human-verification" in gate_page.locator("#form-status").inner_text().lower()
            gate_context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("PASS TOKI booking browser QA: required privacy and booking-terms acknowledgements, terms-version relay, Turnstile gate, exact numeric time validation, package prefill, Supabase public-key request, reference confirmation, failed-request recovery, date validation, and six responsive widths.")


if __name__ == "__main__":
    main()
