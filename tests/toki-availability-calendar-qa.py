#!/usr/bin/env python3
"""Browser QA for the public TOKI SATSUEI monthly availability calendar."""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
SUPABASE_HOST = "https://pjuwrngnrrvdiwqspkic.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_PRGb0-smtTzCm9VHuM9NOQ_ZFh1wKRS"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def main() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "availability.js").read_text(encoding="utf-8")
    edge = (ROOT / "supabase/functions/toki-calendar/index.ts").read_text(encoding="utf-8")
    assert 'id="availability"' in index
    assert 'href="#availability"' in index
    assert 'id="availability-days"' in index
    assert 'status: "eq.confirmed"' in edge
    assert 'select: "confirmed_date,confirmed_start_time,confirmed_end_time"' in edge
    assert 'return jsonResponse({ ok: true, month: requestedMonth, bookings }, 200, origin)' in edge
    assert "contact_value" not in edge and "admin_notes" not in edge and "reference_code" not in edge and "preferred_date" not in edge
    assert "Asia/Manila" in script and "60000" in script
    assert "slotTimeFormatter" in script and "clockTimeFormatter" in script and "clockTimeFormatter.format(new Date())" in script
    assert "consume_portfolio_quota" in edge and "hmacHex" in edge
    assert "availability-retry" in index and "availability-use-date" in index
    assert "availability-today" in index and "aria-pressed" in script
    assert "availability-booked-slot-list" in index and "calendar-booking-count" in script
    assert "Other non-overlapping sessions" in script
    assert "toki-calendar" in script

    today = date.today()
    manila_today = date.fromisoformat(__import__("datetime").datetime.now(ZoneInfo("Asia/Manila")).date().isoformat())
    future_days = [
        manila_today + timedelta(days=offset)
        for offset in range(1, 10)
        if month_key(manila_today + timedelta(days=offset)) == month_key(manila_today)
    ]
    assert len(future_days) >= 2, "Run this test with at least two remaining days in the current Manila month."
    free_date, booked_date = future_days[0], future_days[1]
    current_month = month_key(manila_today)

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    requests: list[dict] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())

            def calendar_response(route):
                request = route.request
                origin = request.headers.get("origin", "*")
                cors = {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "apikey",
                }
                if request.method == "OPTIONS":
                    route.fulfill(status=204, headers=cors)
                    return
                from urllib.parse import urlparse, parse_qs
                month = parse_qs(urlparse(request.url).query).get("month", [current_month])[0]
                requests.append({"month": month, "headers": request.headers})
                if len(requests) == 1:
                    route.fulfill(status=503, content_type="application/json", headers=cors, body=json.dumps({"ok": False}))
                    return
                if month == current_month:
                    bookings = [
                        {"date": booked_date.isoformat(), "start_time": "10:00:00", "end_time": "11:30:00"},
                        {"date": booked_date.isoformat(), "start_time": "14:00:00", "end_time": "15:00:00"},
                    ]
                else:
                    bookings = [
                        {"date": month + "-15", "start_time": "09:00:00", "end_time": "10:00:00"}
                    ]
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    headers=cors,
                    body=json.dumps({"ok": True, "month": month, "bookings": bookings}),
                )

            context.route(SUPABASE_HOST + "/functions/v1/toki-calendar**", calendar_response)
            page = context.new_page()
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.wait_for_function("() => document.querySelector('#availability-retry')?.hidden === false")
            assert page.locator("#availability-retry").is_visible()
            page.locator("#availability-retry").click()
            page.wait_for_function(
                "() => document.querySelector('#availability-updated')?.textContent?.startsWith('UPDATED ')"
            )

            assert page.locator("#availability-month").inner_text().lower().startswith(
                __import__("datetime").datetime.now(ZoneInfo("Asia/Manila")).strftime("%B").lower()
            )
            booked_button = page.locator(f'.calendar-day[data-date="{booked_date.isoformat()}"]')
            assert booked_button.is_enabled(), "Partially booked dates must remain selectable"
            assert booked_button.locator(".calendar-booking-count").inner_text() == "2"
            booked_button.click()
            slots = page.locator("#availability-booked-slot-list li")
            assert slots.count() == 2, "Both confirmed time windows must be shown"
            slot_text = page.locator("#availability-booked-slot-list").inner_text()
            assert "10:00" in slot_text and "11:30" in slot_text and "2:00" in slot_text and "3:00" in slot_text
            assert "non-overlapping" in page.locator("#availability-booked-slot-note").inner_text().lower()
            page.locator("#availability-use-date").click()
            assert page.locator('#inquiry-form input[name="preferred_date"]').input_value() == booked_date.isoformat()
            assert "2 confirmed time windows" in page.locator("#form-status").inner_text().lower()

            page.locator(f'.calendar-day[data-date="{free_date.isoformat()}"]').click()
            assert page.locator(f'.calendar-day[data-date="{free_date.isoformat()}"]').get_attribute("aria-pressed") == "true"
            assert "no confirmed time windows" in page.locator("#availability-booked-slot-list").inner_text().lower()
            page.locator("#availability-use-date").click()
            assert page.locator('#inquiry-form input[name="preferred_date"]').input_value() == free_date.isoformat()
            assert "inquiry only" in page.locator("#form-status").inner_text().lower()

            previous_month = page.locator("#availability-month").inner_text()
            page.locator("#availability-next").click()
            page.wait_for_function(
                "(month) => document.querySelector('#availability-month')?.textContent !== month",
                arg=previous_month,
            )
            page.wait_for_function("() => document.querySelector('#availability-days')?.getAttribute('aria-busy') === 'false'")
            next_month = requests[-1]["month"]
            assert next_month != current_month
            next_booked_button = page.locator(f'.calendar-day[data-date="{next_month}-15"]')
            assert next_booked_button.is_enabled()
            assert next_booked_button.locator(".calendar-booking-count").inner_text() == "1"
            assert requests[0]["headers"].get("apikey") == PUBLISHABLE_KEY

            page.locator("#availability-previous").click()
            page.wait_for_function(
                "(month) => document.querySelector('#availability-month')?.textContent === month",
                arg=previous_month,
            )
            page.locator("#availability-next").click()
            page.wait_for_function(
                "(month) => document.querySelector('#availability-month')?.textContent !== month",
                arg=previous_month,
            )
            page.locator("#availability-today").click()
            page.wait_for_function(
                "(month) => document.querySelector('#availability-month')?.textContent === month",
                arg=previous_month,
            )

            for width in [320, 360, 390, 680, 768, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 850})
                page.wait_for_timeout(30)
                page_width = page.evaluate("() => document.documentElement.scrollWidth")
                assert page_width <= width + 1, f"Availability calendar overflow at {width}px ({page_width}px)"

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("PASS TOKI availability calendar QA: private time-window feed, multiple same-day bookings, visible booked times, partially booked date selection, month navigation, inquiry prefill, retry recovery, automatic refresh, and seven responsive widths.")


if __name__ == "__main__":
    main()
