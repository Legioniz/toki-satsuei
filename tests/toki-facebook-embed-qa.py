#!/usr/bin/env python3
"""Responsive and fallback regression checks for the embedded Facebook Page timeline."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

PUBLIC = Path(__file__).resolve().parents[1]
PAGE_URL = "https://www.facebook.com/tokisatsuiephotography/"
VIEWPORTS = [
    (1440, 900), (1024, 768), (820, 900), (768, 900),
    (680, 800), (430, 932), (390, 844), (360, 800),
    (320, 568), (844, 390), (390, 844),
]


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
    requests = []
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
            context.route("https://www.facebook.com/**", lambda route: route.abort())

            def serve_page_plugin(route):
                requests.append(route.request.url)
                route.fulfill(
                    status=200,
                    content_type="text/html",
                    body="<!doctype html><html><body>Mock Facebook Page Plugin</body></html>",
                )

            # Register the specific mock after the general Facebook block rule.
            context.route("https://www.facebook.com/plugins/page.php**", serve_page_plugin)

            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            frame = page.locator("#facebook-page-embed")
            assert frame.count() == 1, "Facebook Page iframe is missing"
            assert frame.get_attribute("loading") == "lazy", "Facebook iframe should be lazy-loaded"
            assert frame.get_attribute("title") == "TOKI SATSUEI Facebook Page timeline"

            fallback = page.locator("#facebook-feed-help a")
            assert fallback.get_attribute("href") == PAGE_URL, "Direct Facebook fallback URL is incorrect"
            assert fallback.get_attribute("target") == "_blank"
            assert "noopener" in (fallback.get_attribute("rel") or "")
            assert "noreferrer" in (fallback.get_attribute("rel") or "")

            page.locator("#facebook-updates").scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            page.wait_for_function(
                """() => {
                    const iframe = document.querySelector("#facebook-page-embed");
                    return iframe && iframe.dataset.embedWidth &&
                        new URL(iframe.src).searchParams.get("width") === iframe.dataset.embedWidth;
                }""",
                timeout=5000,
            )

            checks = 0
            requested_widths = set()
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function(
                    """() => {
                        const shell = document.querySelector(".facebook-embed-shell");
                        const iframe = document.querySelector("#facebook-page-embed");
                        if (!shell || !iframe || !shell.clientWidth) return false;
                        const expected = Math.max(180, Math.min(500, Math.round(shell.clientWidth)));
                        const url = new URL(iframe.src);
                        return Number(iframe.dataset.embedWidth) === expected &&
                            url.searchParams.get("width") === String(expected) &&
                            url.searchParams.get("adapt_container_width") === "true";
                    }""",
                    timeout=5000,
                )
                page.wait_for_timeout(220)
                state = page.evaluate(
                    """() => {
                        const shell = document.querySelector(".facebook-embed-shell");
                        const iframe = document.querySelector("#facebook-page-embed");
                        const shellRect = shell.getBoundingClientRect();
                        const frameRect = iframe.getBoundingClientRect();
                        return {
                            width: Number(iframe.dataset.embedWidth),
                            shellWidth: shell.clientWidth,
                            shellRight: shellRect.right,
                            frameRight: frameRect.right,
                            documentWidth: document.documentElement.scrollWidth,
                            viewportWidth: innerWidth,
                            loading: iframe.loading,
                            title: iframe.title
                        };
                    }"""
                )
                assert state["frameRight"] <= state["shellRight"] + 1, (
                    f"Facebook iframe exceeds its shell at {width}px: {state}"
                )
                assert state["documentWidth"] <= width + 1, (
                    f"Facebook feed causes horizontal page overflow at {width}px: {state}"
                )
                requested_widths.add(str(state["width"]))
                checks += 1

            assert requests, "The Facebook plugin iframe was never requested by the browser"
            for request_url in requests:
                params = parse_qs(urlparse(request_url).query)
                assert params.get("href", [None])[0] == PAGE_URL
                assert params.get("tabs", [None])[0] == "timeline"
                assert params.get("adapt_container_width", [None])[0] == "true"
            seen_network_widths = {
                parse_qs(urlparse(url).query).get("width", [None])[0]
                for url in requests
            }
            assert seen_network_widths.issubset(requested_widths | seen_network_widths)
            assert not page_errors, "Homepage JavaScript errors: " + "; ".join(page_errors)

            browser.close()
        print(
            "PASS TOKI SATSUEI Facebook feed QA: "
            f"{checks} viewport/orientation checks, {len(requests)} mocked plugin request(s)."
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
