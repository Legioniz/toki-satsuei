#!/usr/bin/env python3
"""Browser QA for the main-site Facebook post rail and embed behavior."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
P1 = "https://www.facebook.com/tokisatsuiephotography/posts/123456789"
P2 = "https://www.facebook.com/tokisatsuiephotography/reel/987654321"
SAMPLE = {
    "schema_version": 2,
    "posts": [
        {"url": P1, "label": "LATEST FRAME", "category": "cosplay", "featured": True},
        {"url": P2, "label": "EVENT RECAP", "category": "events", "featured": False},
    ],
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main():
    assert not (ROOT / "feed-manager.html").exists(), "Feed Manager page must be removed from the repository."
    assert not (ROOT / "feed-manager.js").exists(), "Feed Manager script must be removed from the repository."
    assert not (ROOT / "feed-manager.css").exists(), "Feed Manager stylesheet must be removed from the repository."

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    errors = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            context.route(
                "**/facebook-posts.json**",
                lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(SAMPLE)),
            )

            def mock_facebook_sdk(route):
                route.fulfill(
                    status=200,
                    content_type="application/javascript",
                    body="""
                    window.__fbParseCount = 0;
                    window.FB = {
                      init: function () {},
                      XFBML: {
                        parse: function (root) {
                          window.__fbParseCount += root.querySelectorAll(".fb-post").length;
                          root.querySelectorAll(".fb-post").forEach(function (container) {
                            var iframe = document.createElement("iframe");
                            iframe.title = "Mock public Facebook post";
                            iframe.style.height = "420px";
                            container.appendChild(iframe);
                          });
                        }
                      }
                    };
                    """,
                )

            context.route("https://connect.facebook.net/**", mock_facebook_sdk)

            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.locator(".facebook-embed-card iframe").first.wait_for(state="attached", timeout=7000)

            cards = page.locator(".facebook-embed-card")
            assert cards.count() == 2
            assert cards.nth(0).locator(".facebook-embed-category").inner_text() == "Cosplay"
            assert "is-featured" in cards.nth(0).get_attribute("class")
            assert page.evaluate("window.__fbParseCount") == 2
            assert page.locator('a[href*="feed-manager"]').count() == 0
            assert page.locator("#facebook-feed-scroll-controls").is_visible()
            assert page.locator("#facebook-feed-next").is_enabled()
            assert page.locator("#facebook-feed-previous").is_disabled()
            assert page.locator("#facebook-feed-list").evaluate(
                "(element) => getComputedStyle(element).scrollSnapType"
            ).startswith("x")

            page.locator("#facebook-feed-next").click()
            page.wait_for_function("document.querySelector('#facebook-feed-list').scrollLeft > 4")
            page.wait_for_function("document.querySelector('#facebook-feed-previous').disabled === false")
            page.locator("#facebook-feed-previous").click()
            page.wait_for_function("document.querySelector('#facebook-feed-list').scrollLeft < 4")

            page.locator("#facebook-feed-search").fill("event")
            assert page.locator(".facebook-embed-card").count() == 1
            assert page.locator("#facebook-feed-scroll-controls").is_hidden()
            page.locator("#facebook-feed-search").fill("")
            page.locator(".facebook-feed-filter").filter(has_text="Cosplay").click()
            assert page.locator(".facebook-embed-card").count() == 1
            page.locator(".facebook-feed-filter").filter(has_text="All").click()

            checks = 0
            for width in [1440, 1024, 820, 680, 430, 390, 360, 320]:
                page.set_viewport_size({"width": width, "height": 850})
                measurements = page.evaluate(
                    """() => {
                      const column = document.querySelector(".facebook-feed-column").getBoundingClientRect();
                      const rail = document.querySelector("#facebook-feed-list");
                      const railRect = rail.getBoundingClientRect();
                      const cards = [...document.querySelectorAll(".facebook-embed-card")];
                      return {
                        documentWidth: document.documentElement.scrollWidth,
                        columnWidth: column.width,
                        railWidth: railRect.width,
                        railRight: railRect.right,
                        cardWidths: cards.map(card => card.getBoundingClientRect().width),
                        railScrollWidth: rail.scrollWidth,
                        railClientWidth: rail.clientWidth
                      };
                    }"""
                )
                assert measurements["documentWidth"] <= width + 1, (
                    "Document overflow at " + str(width) + "px: " + repr(measurements)
                )
                assert measurements["columnWidth"] > 0
                assert measurements["railWidth"] <= measurements["columnWidth"] + 1
                assert measurements["railRight"] <= width + 1
                assert all(card_width <= measurements["railClientWidth"] + 1 for card_width in measurements["cardWidths"])
                if len(measurements["cardWidths"]) > 1:
                    assert measurements["railScrollWidth"] > measurements["railClientWidth"]
                checks += 1

            manager_response = page.request.get(base + "/feed-manager.html")
            assert manager_response.status == 404

            empty_context = browser.new_context(viewport={"width": 390, "height": 850})
            empty_context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            empty_context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            empty_context.route(
                "**/facebook-posts.json**",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"schema_version": 2, "posts": []}),
                ),
            )
            empty_page = empty_context.new_page()
            empty_page.on("pageerror", lambda error: errors.append(str(error)))
            empty_page.goto(base + "/index.html", wait_until="domcontentloaded")
            empty_page.locator(".facebook-feed-status").filter(has_text="READY TO GROW").wait_for(timeout=5000)
            assert empty_page.locator(".facebook-feed-tools").is_hidden()
            assert empty_page.locator("#facebook-feed-scroll-controls").is_hidden()
            assert empty_page.locator(".facebook-state-link").get_attribute("href").startswith("https://www.facebook.com/")
            empty_context.close()

            assert not errors, "JavaScript errors: " + "; ".join(errors)
            browser.close()

        print(
            "PASS TOKI SATSUEI feature QA: embedded post metadata, native post embeds, "
            "horizontal scrolling, previous/next controls, search, category filters, "
            "8 responsive widths, empty state, and complete Feed Manager removal."
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
