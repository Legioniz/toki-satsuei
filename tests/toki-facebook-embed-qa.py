#!/usr/bin/env python3
"""Browser QA for the rendered TOKI SATSUEI Facebook post feed."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


PUBLIC = Path(__file__).resolve().parents[1]
PAGE_URL = "https://www.facebook.com/tokisatsuiephotography/"
POST_URL = "https://www.facebook.com/tokisatsuiephotography/posts/123456789"
VIEWPORTS = [
    (1440, 900), (1024, 768), (820, 900), (768, 900),
    (680, 800), (430, 932), (390, 844), (360, 800),
    (320, 568), (844, 390), (390, 844),
]
SAMPLE = {
    "schema_version": 1,
    "status": "ready",
    "updated_at": "2026-11-14T03:00:00+00:00",
    "page": {"name": "TOKI SATSUEI", "url": PAGE_URL},
    "posts": [{
        "id": "page_123",
        "message": "A real post preview should render as text. <script>window.feedInjected = true</script>",
        "created_at": "2026-11-14T02:45:00+00:00",
        "permalink_url": POST_URL,
        "image_url": "https://scontent.xx.fbcdn.net/sample.jpg",
    }],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    feed_requests = []
    external_facebook_requests = []
    page_errors = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            context.route("https://media.base44.com/**", lambda route: route.abort())

            def serve_feed(route):
                feed_requests.append(route.request.url)
                route.fulfill(status=200, content_type="application/json", body=json.dumps(SAMPLE))

            context.route("**/facebook-feed.json**", serve_feed)
            context.route("https://scontent.xx.fbcdn.net/**", lambda route: route.fulfill(
                status=200, content_type="image/gif",
                body=bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")
            ))
            context.route("https://www.facebook.com/**", lambda route: external_facebook_requests.append(route.request.url) or route.abort())

            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.locator(".facebook-post-card").wait_for(state="visible", timeout=7000)

            assert page.locator("#facebook-page-embed").count() == 0, "The old opaque Page iframe must not be the feed renderer"
            assert page.locator(".fb-page").count() == 0, "The page should render first-party feed cards, not an empty FB SDK container"
            assert page.locator(".facebook-post-card").count() == 1, "A fetched post should render as a visible card"
            card = page.locator(".facebook-post-card").first
            assert "TOKI SATSUEI" in card.inner_text()
            assert "<script>window.feedInjected = true</script>" in card.inner_text(), "Post text must be rendered as text, not HTML"
            assert card.locator("script").count() == 0, "Facebook post content must never be injected as markup"
            assert card.locator(".facebook-post-image").count() == 1
            assert card.locator(".facebook-post-image").get_attribute("alt")
            assert card.locator(".facebook-post-action--react").get_attribute("href") == POST_URL
            assert card.locator(".facebook-post-action--comment").get_attribute("href") == POST_URL
            assert "facebook.com/sharer/sharer.php" in card.locator(".facebook-post-action--share").get_attribute("href")
            for action in card.locator(".facebook-post-action").all():
                assert action.get_attribute("target") == "_blank"
                assert "noopener" in (action.get_attribute("rel") or "")
                assert "noreferrer" in (action.get_attribute("rel") or "")
            assert "PAGE FEED" in page.locator("#facebook-feed-status").inner_text()
            assert "SYNCED" in page.locator("#facebook-feed-status").inner_text()
            assert page.locator(".facebook-story-link").get_attribute("href") == PAGE_URL
            assert page.locator(".facebook-follow-link").get_attribute("href") == PAGE_URL
            assert feed_requests, "The same-origin feed snapshot was not requested"

            checks = 0
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(100)
                state = page.evaluate(
                    """() => ({
                        viewport: innerWidth,
                        document: document.documentElement.scrollWidth,
                        feed: document.querySelector(".facebook-feed-column")?.getBoundingClientRect().width,
                        cards: [...document.querySelectorAll(".facebook-post-card")].map(card => ({
                            right: card.getBoundingClientRect().right,
                            width: card.getBoundingClientRect().width
                        }))
                    })"""
                )
                assert state["document"] <= width + 1, f"Horizontal page overflow at {width}px: {state}"
                assert state["feed"] > 0, f"Feed column collapsed at {width}px: {state}"
                assert all(card["right"] <= width + 1 for card in state["cards"]), f"Feed card overflow at {width}px: {state}"
                checks += 1

            before = len(feed_requests)
            page.locator("#facebook-feed-refresh").click()
            page.wait_for_function("document.querySelectorAll('.facebook-post-card').length === 1")
            assert len(feed_requests) > before, "Reload feed did not request a fresh snapshot"

            setup_page = context.new_page()
            setup_page.route("**/facebook-feed.json**", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps({"schema_version": 1, "status": "setup_required", "updated_at": None, "posts": []})
            ))
            setup_page.goto(base + "/index.html", wait_until="domcontentloaded")
            setup_page.locator(".facebook-feed-state--setup").wait_for(state="visible", timeout=7000)
            assert "FACEBOOK CONNECTION NEEDED" in setup_page.locator("#facebook-feed-status").inner_text()
            assert "secure Page connection" in setup_page.locator(".facebook-feed-state").inner_text()
            assert setup_page.locator(".facebook-state-link").get_attribute("href") == PAGE_URL

            error_page = context.new_page()
            error_page.route("**/facebook-feed.json**", lambda route: route.fulfill(status=503, body="Unavailable"))
            error_page.goto(base + "/index.html", wait_until="domcontentloaded")
            error_page.locator(".facebook-feed-state--error").wait_for(state="visible", timeout=7000)
            assert "FEED COULD NOT LOAD" in error_page.locator("#facebook-feed-status").inner_text()
            assert error_page.locator(".facebook-state-link").get_attribute("href") == PAGE_URL

            assert not page_errors, "Homepage JavaScript errors: " + "; ".join(page_errors)
            assert not external_facebook_requests, "The page should not call Facebook from the visitor's browser with private credentials"
            browser.close()

        print(
            "PASS TOKI SATSUEI Facebook feed QA: "
            f"{checks} viewport/orientation checks, rendered public-post cards, secure text handling, "
            "working reload and post actions, setup-required state, and network-error fallback."
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
