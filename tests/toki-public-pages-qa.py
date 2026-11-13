#!/usr/bin/env python3
"""Public-page, policy, 404, and search-discovery QA for TOKI SATSUEI."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://legioniz.github.io/toki-satsuei"
PUBLIC_PAGES = ["index.html", "library.html", "policies.html"]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    for filename in [*PUBLIC_PAGES, "404.html", "policies.css", "robots.txt", "sitemap.xml"]:
        path = ROOT / filename
        assert path.is_file() and path.stat().st_size > 0, f"Missing public page asset: {filename}"

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    archive = (ROOT / "library.html").read_text(encoding="utf-8")
    policies = (ROOT / "policies.html").read_text(encoding="utf-8")
    not_found = (ROOT / "404.html").read_text(encoding="utf-8")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")

    assert 'id="faq"' in index and len(re.findall(r"<summary>", index)) >= 7
    assert "honest practice and detail studies, not a finished cosplay or portrait client portfolio" in index
    assert "only after the people featured give permission" in index.lower()
    assert 'href="./policies.html"' in index and 'href="./policies.html"' in archive
    assert 'href="./policies.css?' in policies
    assert 'id="consent"' in policies and 'id="pricing"' in policies and 'id="changes"' in policies
    assert "within 7 days after the session" in policies
    assert "deposit, payment deadline" in policies
    assert 'name="robots" content="noindex,follow"' in not_found
    assert "Return home" in not_found and "Browse the archive" in not_found
    assert "Sitemap: " + BASE_URL + "/sitemap.xml" in robots

    tree = ET.parse(ROOT / "sitemap.xml")
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text for node in tree.findall(".//sm:loc", ns)]
    expected = [BASE_URL + "/", BASE_URL + "/library.html", BASE_URL + "/policies.html"]
    assert locations == expected, f"Unexpected sitemap URLs: {locations}"

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 390, "height": 844})
            context.route("https://**", lambda route: route.abort())
            for page_name in ["index.html", "library.html", "policies.html", "404.html"]:
                page = context.new_page()
                page.goto(base + "/" + page_name, wait_until="domcontentloaded")
                assert page.locator("main#main-content").count() == 1, f"{page_name}: main landmark missing"
                assert page.locator(".skip-link").get_attribute("href") == "#main-content"
                assert page.locator("title").inner_text() or page.title()
                for width in [320, 390, 680, 768, 1024, 1440]:
                    page.set_viewport_size({"width": width, "height": 850})
                    page.wait_for_timeout(30)
                    width_check = page.evaluate("() => document.documentElement.scrollWidth")
                    assert width_check <= width + 1, f"{page_name}: horizontal overflow at {width}px ({width_check}px)"
                page.close()

            faq = context.new_page()
            faq.goto(base + "/index.html#faq", wait_until="domcontentloaded")
            faq.locator(".faq-list details").first.locator("summary").click()
            assert faq.locator(".faq-list details").first.evaluate("(node) => node.open")
            faq.close()

            policy = context.new_page()
            policy.goto(base + "/policies.html#consent", wait_until="domcontentloaded")
            assert policy.locator("#consent").is_visible()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("PASS TOKI SATSUEI public-page QA: FAQ content, policy anchors, consent wording, booking terms, 404 recovery page, sitemap, robots, skip links, and six responsive widths.")


if __name__ == "__main__":
    main()
