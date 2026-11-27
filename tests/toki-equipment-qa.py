#!/usr/bin/env python3
"""Browser regression checks for the interactive equipment field study."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


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
            page.wait_for_function(
                "document.querySelector('[data-equipment-root]')?.dataset.equipmentReady === 'true'",
                timeout=10000,
            )

            root = page.locator("[data-equipment-root]")
            assert root.count() == 1, "Equipment section must appear once on the homepage"
            assert page.locator('a[href="#equipment"]').count() == 1, "Equipment navigation anchor is missing"

            camera_tab = root.locator('[data-equipment-component="camera"]')
            lens_tab = root.locator('[data-equipment-component="lens"]')
            assert camera_tab.get_attribute("aria-selected") == "true"
            lens_tab.click()
            assert lens_tab.get_attribute("aria-pressed") == "true"
            assert root.locator('[data-spec-panel="lens"]').is_visible(), "Lens details did not become visible"
            assert root.locator('[data-spec-panel="camera"]').is_hidden(), "Camera details should be hidden while lens is selected"

            root.locator('[data-equipment-mode="2d"]').click()
            assert root.locator("[data-equipment-stage]").get_attribute("data-view") == "2d"
            assert root.locator('[data-blueprint-panel="front"]').is_visible()
            root.locator('[data-blueprint-view="rear"]').click()
            assert root.locator('[data-blueprint-panel="rear"]').is_visible(), "Rear schematic did not activate"
            assert root.locator('[data-blueprint-panel="front"]').is_hidden(), "Only one 2D view should be visible"
            root.locator('[data-blueprint-view="side"]').click()
            assert root.locator('[data-blueprint-panel="side"]').is_visible(), "Side schematic did not activate"

            root.locator('[data-equipment-mode="3d"]').click()
            assert root.locator("[data-camera-model]").is_visible()
            before = root.locator("[data-camera-object]").evaluate("(node) => getComputedStyle(node).getPropertyValue('--camera-ry')")
            root.locator("[data-rotate-right]").click()
            page.wait_for_timeout(80)
            after = root.locator("[data-camera-object]").evaluate("(node) => getComputedStyle(node).getPropertyValue('--camera-ry')")
            assert before != after, "3D rotation control did not change the model orientation"

            camera_tab.click()
            assert root.locator('[data-spec-panel="camera"]').is_visible()
            assert "18.0 MP" in root.locator('[data-spec-panel="camera"]').inner_text()
            assert "Version-dependent" in root.locator('[data-spec-panel="lens"]').inner_text()

            for width in (320, 360, 390, 430, 600, 768, 900, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(30)
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
        server.server_close()
    print("TOKI equipment model, controls, specifications, and responsive layout: PASS")


if __name__ == "__main__":
    main()
