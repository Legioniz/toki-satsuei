#!/usr/bin/env python3
"""QA test suite for TOKI SATSUEI owner administration dashboard."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUPABASE_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co"

MOCK_BOOKINGS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "reference_code": "TOKI-A1B2C3D4",
        "name": "Alex Cosplayer",
        "contact_method": "instagram",
        "contact_value": "@alex.cosplay",
        "session_type": "Duo Session",
        "preferred_date": "2026-12-01",
        "preferred_time": "14:30",
        "alternate_date": "2026-12-02",
        "location": "Quezon Memorial Circle",
        "participants": 2,
        "notes": "Duo character shoot",
        "status": "reviewing",
        "confirmed_date": None,
        "confirmed_start_time": None,
        "confirmed_end_time": None,
        "total_price": 500,
        "reservation_fee": 100,
        "reservation_fee_paid": False,
        "balance_paid": False,
        "delivery_folder_url": None,
        "delivery_status": "pending",
        "delivery_token_hash": None,
        "admin_notes": "Needs lighting check",
        "created_at": "2026-11-20T10:00:00Z",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "reference_code": "TOKI-E5F6G7H8",
        "name": "Rhea Portrait",
        "contact_method": "email",
        "contact_value": "rhea@example.com",
        "session_type": "Toki Portraits",
        "preferred_date": "2026-12-05",
        "preferred_time": "16:00",
        "alternate_date": None,
        "location": "UP Diliman",
        "participants": 1,
        "notes": "Solo golden hour",
        "status": "confirmed",
        "confirmed_date": "2026-12-05",
        "confirmed_start_time": "16:00",
        "confirmed_end_time": "16:30",
        "total_price": 350,
        "reservation_fee": 70,
        "reservation_fee_paid": True,
        "balance_paid": False,
        "delivery_folder_url": None,
        "delivery_status": "pending",
        "delivery_token_hash": None,
        "admin_notes": "Deposit verified via GCash",
        "created_at": "2026-11-21T11:00:00Z",
    },
]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    # 1. Structural HTML verification
    admin_html = (ROOT / "admin.html").read_text(encoding="utf-8")
    assert 'id="admin-auth-section"' in admin_html
    assert 'id="admin-dashboard-section"' in admin_html
    assert 'id="admin-login-form"' in admin_html
    assert 'id="admin-search-input"' in admin_html
    assert 'id="admin-booking-tbody"' in admin_html
    assert 'id="admin-detail-modal"' in admin_html
    assert 'toki-admin.css' in admin_html
    assert 'admin.js' in admin_html

    # 2. Browser interaction test with mocked auth and Supabase REST
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())

            # Seed a valid admin session in sessionStorage
            session_data = json.dumps({
                "access_token": "test-mock-jwt-token",
                "expires_at": 9999999999,
                "user": {"email": "owner@tokisatsuei.com"},
                "refresh_token": "legacy-refresh-token-must-not-persist",
            })
            context.add_init_script(f"""
                sessionStorage.setItem("toki_admin_session", JSON.stringify({session_data}));
            """)

            captured_updates = []

            # Route Supabase REST requests
            def mock_supabase(route):
                req = route.request
                if "auth/v1/token" in req.url:
                    route.fulfill(status=200, content_type="application/json", body=session_data)
                    return
                if "auth/v1/logout" in req.url:
                    route.fulfill(status=204, body="")
                    return
                if "toki_booking_requests" in req.url:
                    if req.method == "PATCH":
                        captured_updates.append(req.post_data_json)
                        route.fulfill(status=204, body="")
                    else:
                        route.fulfill(status=200, content_type="application/json", body=json.dumps(MOCK_BOOKINGS))
                    return
                route.continue_()

            context.route(f"{SUPABASE_URL}/**", mock_supabase)

            page = context.new_page()
            page.goto(base_url + "/admin.html", wait_until="domcontentloaded")

            # Check that dashboard section is visible and auth is hidden
            assert page.locator("#admin-dashboard-section").is_visible()
            assert not page.locator("#admin-auth-section").is_visible()

            # Check that user email is displayed in header
            assert "owner@tokisatsuei.com" in page.locator("#admin-user-email").inner_text()
            stored_session = page.evaluate("sessionStorage.getItem('toki_admin_session')")
            assert "refresh_token" not in stored_session, "Admin refresh token was persisted in sessionStorage"

            # Wait for table rows to render
            page.locator("tr[data-id]").first.wait_for(state="visible", timeout=7000)
            rows = page.locator("#admin-booking-tbody tr[data-id]")
            assert rows.count() == 2

            # Check metrics
            assert page.locator("#metric-total").inner_text() == "2"
            assert page.locator("#metric-review").inner_text() == "1"
            assert page.locator("#metric-confirmed").inner_text() == "1"

            # Filter by confirmed
            page.locator('.admin-pill[data-status="confirmed"]').click()
            visible_rows = page.locator("#admin-booking-tbody tr[data-id]")
            assert visible_rows.count() == 1
            assert "Rhea Portrait" in visible_rows.first.inner_text()

            # Reset filter to all
            page.locator('.admin-pill[data-status="all"]').click()
            assert page.locator("#admin-booking-tbody tr[data-id]").count() == 2

            # Test search filter
            page.locator("#admin-search-input").fill("Alex")
            assert page.locator("#admin-booking-tbody tr[data-id]").count() == 1
            assert "Alex Cosplayer" in page.locator("#admin-booking-tbody tr[data-id]").first.inner_text()
            page.locator("#admin-search-input").fill("")
            assert page.locator("#admin-booking-tbody tr[data-id]").count() == 2

            # Click row to open modal
            page.locator('button.admin-action-btn:has-text("Manage")').first.click()
            dialog = page.locator("#admin-detail-modal")
            assert dialog.is_visible()
            assert "Alex Cosplayer" in page.locator("#modal-client-name").inner_text()
            assert page.locator("#modal-status-select").input_value() == "reviewing"
            assert page.evaluate("document.activeElement?.id") == "modal-close-btn", "Admin modal did not move focus inside on open"
            page.locator("#modal-save-btn").focus()
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement?.id") == "modal-close-btn", "Admin modal Tab focus escaped instead of wrapping"
            page.keyboard.press("Shift+Tab")
            assert page.evaluate("document.activeElement?.id") == "modal-save-btn", "Admin modal reverse Tab focus did not wrap"
            page.keyboard.press("Escape")
            assert dialog.is_hidden(), "Escape did not close the admin modal"
            assert page.locator("button.admin-action-btn").first.evaluate("(el)=>el===document.activeElement"), "Admin modal did not restore focus to its opener"
            page.locator("button.admin-action-btn").first.click()
            assert dialog.is_visible()

            # Test token generator
            page.locator("#modal-gen-token-btn").click()
            token_val = page.locator("#modal-delivery-token").input_value()
            assert token_val.startswith("toki-") and len(token_val) == 69
            assert all(character in "0123456789abcdef" for character in token_val[5:]), "Delivery token must use 256 bits from Web Crypto"

            # Save the delivery key. Only its SHA-256 hash may be sent to Supabase.
            page.locator("#modal-delivery-url").fill("https://drive.google.com/drive/folders/private-test")
            page.locator("#modal-save-btn").click()
            page.wait_for_function("document.querySelector('#admin-detail-modal').hidden")
            assert captured_updates, "Admin booking update was not sent"
            update_payload = captured_updates[-1]
            assert "delivery_token_hash" in update_payload
            assert "delivery_token" not in update_payload
            assert update_payload["delivery_token_hash"] != token_val
            assert len(update_payload["delivery_token_hash"]) == 64
            assert all(character in "0123456789abcdef" for character in update_payload["delivery_token_hash"])
            assert update_payload["delivery_status"] == "ready"
            assert "delivery_expires_at" in update_payload
            assert page.locator("#modal-delivery-token").input_value() == ""
            assert not dialog.is_visible()

            # Test sign out
            page.locator("#admin-logout-btn").click()
            assert page.locator("#admin-auth-section").is_visible()
            assert not page.locator("#admin-dashboard-section").is_visible()

            browser.close()
    finally:
        server.shutdown()

    print("PASS TOKI admin dashboard QA: auth gate, session persistence, metric cards, status filtering, client search, detail modal editor, token generator, and sign out.")


if __name__ == "__main__":
    main()
