#!/usr/bin/env python3
"""QA test suite for TOKI SATSUEI client gallery delivery portal."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SUPABASE_URL = "https://pjuwrngnrrvdiwqspkic.supabase.co"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    # 1. Structural HTML verification
    client_html = (ROOT / "client-gallery.html").read_text(encoding="utf-8")
    assert 'id="client-gate-section"' in client_html
    assert 'id="client-gallery-section"' in client_html
    assert 'id="client-token-form"' in client_html
    assert 'id="client-token-input"' in client_html
    assert 'type="password" id="client-token-input"' in client_html
    assert 'id="client-photo-grid"' in client_html
    assert 'id="client-submit-selection-btn"' in client_html
    assert 'id="client-delivery-link"' in client_html
    assert "Google Drive" not in client_html
    client_script = (ROOT / "client-gallery.js").read_text(encoding="utf-8")
    assert "drive.google.com" not in client_script
    assert 'toki-client.css' in client_html
    assert 'client-gallery.js' in client_html

    # 2. Browser interaction test with mocked Supabase RPC
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

            # Route Supabase RPC calls
            gallery_lookup_count = 0
            def mock_rpc(route):
                nonlocal gallery_lookup_count
                req = route.request
                if "toki_get_client_gallery" in req.url:
                    gallery_lookup_count += 1
                    delivery_url = "https://delivery.example/clients/test-delivery"
                    if gallery_lookup_count > 1:
                        delivery_url = "http://delivery.example/insecure"
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({
                        "ok": True,
                        "client_name": "Maya Lin",
                        "session_type": "Signature Session",
                        "confirmed_date": "2026-11-20",
                        "delivery_status": "ready",
                        "delivery_folder_url": delivery_url,
                        "client_selected_photos": ["frame-001"],
                    }))
                    return
                if "toki_submit_client_selection" in req.url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({
                        "ok": True,
                        "saved_count": 2,
                    }))
                    return
                route.continue_()

            context.route(f"{SUPABASE_URL}/**", mock_rpc)

            page = context.new_page()
            # Auto-dismiss alerts
            page.on("dialog", lambda dialog: dialog.accept())

            page.goto(base_url + "/client-gallery.html", wait_until="domcontentloaded")

            # Check that gate is visible and gallery is hidden
            assert page.locator("#client-gate-section").is_visible()
            assert not page.locator("#client-gallery-section").is_visible()

            # Submit token
            page.locator("#client-token-input").fill("token-maya-123")
            page.locator('#client-token-form button[type="submit"]').click()

            # Wait for gallery to appear
            page.locator("#client-gallery-section").wait_for(state="visible", timeout=7000)
            assert not page.locator("#client-gate-section").is_visible()

            # Check personalized greeting and session info
            assert "Maya Lin" in page.locator("#client-greeting").inner_text()
            assert "Signature Session" in page.locator("#client-session-details").inner_text()

            # A provider-neutral HTTPS destination is accepted without hard-coding a storage brand.
            delivery_btn = page.locator("#client-delivery-link")
            assert delivery_btn.is_visible()
            assert delivery_btn.inner_text().lower().startswith("open private delivery")
            assert delivery_btn.get_attribute("href") == "https://delivery.example/clients/test-delivery"

            # Never substitute practice/sample photos for a client's actual delivered images.
            assert page.locator(".client-photo-item").count() == 0
            assert page.locator(".client-gallery-empty").is_visible()
            empty_state = page.locator(".client-gallery-empty").inner_text().lower()
            assert "private delivery link" in empty_state
            assert "private photo preview list has not been connected" in empty_state
            assert "private delivery link" in empty_state
            assert page.locator(".client-selection-summary").is_hidden()

            # Bearer tokens in query strings are not accepted; enter the key into the password field instead.
            page.goto(base_url + "/client-gallery.html?token=token-maya-123", wait_until="domcontentloaded")
            assert page.locator("#client-gate-section").is_visible()
            assert not page.locator("#client-gallery-section").is_visible()
            page.locator("#client-token-input").fill("token-maya-123")
            page.locator('#client-token-form button[type="submit"]').click()
            page.locator("#client-gallery-section").wait_for(state="visible", timeout=7000)
            assert "Maya Lin" in page.locator("#client-greeting").inner_text()
            assert page.locator("#client-delivery-link").is_hidden(), "Insecure HTTP delivery URLs must never be exposed."

            browser.close()
    finally:
        server.shutdown()

    print("PASS TOKI client gallery QA: password-gated private HTTPS delivery, rejected insecure links, no fabricated sample photos, no bearer token query strings, and honest empty-state messaging.")


if __name__ == "__main__":
    main()
