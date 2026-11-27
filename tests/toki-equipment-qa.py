#!/usr/bin/env python3
"""Browser regression checks for the static equipment reference section."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CANON_CAMERA = "https://asia.canon/en/pro-imaging/eos-3000d-kit-ef-s18-55-iii/main/product"
CANON_LENS = "https://global.canon/en/c-museum/product/ef410.html"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/index.html", wait_until="domcontentloaded")

            section = page.locator("#equipment")
            assert section.count() == 1, "Equipment section must appear once on the homepage"
            assert page.locator('a[href="#equipment"]').count() == 1, "Equipment section anchor is missing"
            assert section.locator("[data-equipment-card]").count() == 2, "Camera and lens must be separate cards"
            assert section.locator("[data-camera-model], [data-camera-object], [data-equipment-mode], [data-blueprint-view]").count() == 0, (
                "Retired interactive 3D/2D model controls must not remain"
            )
            assert section.locator("svg, canvas").count() == 0, "Equipment section should not contain model drawings"
            assert page.locator('script[src*="equipment.js"]').count() == 0, "Retired equipment controller is still loaded"

            camera = section.locator('[data-equipment-card="camera"]')
            lens = section.locator('[data-equipment-card="lens"]')
            assert camera.count() == lens.count() == 1
            assert "Canon EOS 3000D" in camera.inner_text()
            assert "18 MP" in camera.inner_text()
            assert "DIGIC 4+" in camera.inner_text()
            assert "9-point AF" in camera.inner_text()
            assert "Canon EF-S 18–55mm" in lens.inner_text()
            assert "Version-dependent" in lens.inner_text()
            assert "revision printed on the lens barrel has not yet been confirmed" in lens.inner_text().lower()

            camera_link = camera.locator(".equipment-source-link")
            lens_link = lens.locator(".equipment-source-link")
            assert camera_link.get_attribute("href") == CANON_CAMERA
            assert lens_link.get_attribute("href") == CANON_LENS
            for link in (camera_link, lens_link):
                assert link.get_attribute("target") == "_blank"
                assert "noopener" in (link.get_attribute("rel") or "")

            for width in (320, 360, 390, 430, 600, 768, 900, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(25)
                dimensions = page.evaluate(
                    """() => ({
                      viewport: document.documentElement.clientWidth,
                      document: document.documentElement.scrollWidth,
                      section: document.querySelector('.equipment-section').scrollWidth,
                      sectionClient: document.querySelector('.equipment-section').clientWidth
                    })"""
                )
                assert dimensions["document"] <= dimensions["viewport"] + 1, (
                    f"Horizontal page overflow at {width}px: {dimensions}"
                )
                assert dimensions["section"] <= dimensions["sectionClient"] + 1, (
                    f"Equipment section overflow at {width}px: {dimensions}"
                )

            assert not errors, "Browser JavaScript errors: " + "; ".join(errors)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    print("TOKI equipment cards, Canon source links, specifications, and responsive layout: PASS")


if __name__ == "__main__":
    main()
