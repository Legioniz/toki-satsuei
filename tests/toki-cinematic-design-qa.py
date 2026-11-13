#!/usr/bin/env python3
"""Regression checks for the cinematic sketchbook / professional portfolio system."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [320, 360, 390, 430, 680, 768, 820, 1024, 1280, 1440]
PAGES = ["index.html", "library.html", "policies.html", "404.html"]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    for filename in [*PAGES, "cinematic.css"]:
        path = ROOT / filename
        assert path.is_file() and path.stat().st_size > 0, f"Missing cinematic asset: {filename}"

    css = (ROOT / "cinematic.css").read_text(encoding="utf-8")
    for selector in [
        ".hero-annotation", ".frame-intention", ".gallery-card",
        ".service-row", ".package-card", ".about-visual",
        ".library-page .archive-shelf", ".facebook-section",
        ".policy-hero", ".not-found-main",
    ]:
        assert selector in css, f"Cinematic system is missing {selector}"

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    archive = (ROOT / "library.html").read_text(encoding="utf-8")
    policy = (ROOT / "policies.html").read_text(encoding="utf-8")
    not_found = (ROOT / "404.html").read_text(encoding="utf-8")
    for label, source in [("home", home), ("archive", archive), ("policies", policy), ("404", not_found)]:
        assert "cinematic.css?v=" in source, f"{label}: cinematic stylesheet is not loaded"
        assert "family=Caveat" in source, f"{label}: handwritten annotation font is not loaded"
        assert 'href="#main-content"' in source, f"{label}: keyboard skip link is missing"

    assert "Stay with<br>the <em>feeling.</em>" in home
    assert "hero-annotation" in home and "frame-intention" in home
    assert home.count('class="gallery-card') == 4, "The early practice contact sheet should contain four authentic frames."
    assert "practice and detail studies" in home.lower()
    assert "only after the people featured give permission" in home.lower()
    assert "<summary>" in home and "policies.html" in home
    assert "Frames, kept<br><em>with intention.</em>" in archive
    assert "working sketchbook" in archive.lower()
    assert "id=\"consent\"" in policy
    assert "FRAME NOT FOUND" in not_found

    manifest_path = ROOT / "media-library.json"
    total_albums = 0
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total_albums = sum(int(category.get("album_count", 0)) for category in manifest.get("categories", []))

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("https://**", lambda route: route.abort())

            for filename in PAGES:
                page = context.new_page()
                page.goto(base + "/" + filename, wait_until="domcontentloaded")
                page.wait_for_selector("main#main-content")
                assert page.locator("link[href*='cinematic.css']").count() == 1, f"{filename}: visual system stylesheet missing"

                for width in VIEWPORTS:
                    page.set_viewport_size({"width": width, "height": 850})
                    page.wait_for_timeout(30)
                    document_width = page.evaluate("() => document.documentElement.scrollWidth")
                    assert document_width <= width + 1, f"{filename}: horizontal overflow at {width}px ({document_width}px)"

                if filename == "index.html":
                    assert page.locator(".hero-annotation").count() == 1
                    assert page.locator(".frame-intention").count() == 1
                    assert page.locator(".gallery-card img[alt]").count() == 4
                    page.set_viewport_size({"width": 390, "height": 844})
                    annotation = page.locator(".hero-annotation").bounding_box()
                    hero_art = page.locator(".hero-art").bounding_box()
                    assert annotation and hero_art
                    assert annotation["x"] >= hero_art["x"] - 1 and annotation["x"] + annotation["width"] <= hero_art["x"] + hero_art["width"] + 1
                    cards = page.locator(".gallery-card").all()
                    widths = [card.bounding_box()["width"] for card in cards]
                    assert max(widths) - min(widths) < 2, f"Mobile contact sheet should stack to a single column: {widths}"

                if filename == "library.html" and total_albums == 0:
                    page.wait_for_selector(".archive-shelf", timeout=3500)
                    assert page.locator(".archive-shelf").count() == 6, "Empty archive should retain all six styled collection shelves."

                page.close()

            faq = context.new_page()
            faq.goto(base + "/index.html#faq", wait_until="domcontentloaded")
            faq.locator(".faq-list details").first.locator("summary").click()
            assert faq.locator(".faq-list details").first.evaluate("(node) => node.open")
            faq.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("PASS cinematic design QA: emotional hero, authentic contact sheet, sketchbook annotations, archive shelves, consistent page styling, and no horizontal overflow across ten responsive widths.")


if __name__ == "__main__":
    main()
