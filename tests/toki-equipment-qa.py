#!/usr/bin/env python3
"""Browser regression checks for the 2D equipment angles and on-demand 3D viewer."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / "media-library" / "equipment" / "eos-3000d-angle-sprite.webp"
SKETCHFAB_MODEL = "https://sketchfab.com/3d-models/canon-eos-3000-7d57163f3bec464cbb213428e1c37cf7"
SKETCHFAB_EMBED = "https://sketchfab.com/models/7d57163f3bec464cbb213428e1c37cf7/embed"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    assert SPRITE.is_file() and SPRITE.stat().st_size > 5000, "Five-angle 2D WebP sprite is missing or incomplete."
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    csp = next((line for line in headers.splitlines() if "Content-Security-Policy:" in line), "")
    frame_src = next((part.strip() for part in csp.split(";") if part.strip().startswith("frame-src ")), "")
    assert "https://sketchfab.com" in frame_src, (
        "The deployed Content Security Policy must allow the Sketchfab iframe host."
    )
    assert "https://sketchfab.com/models/7d57163f3bec464cbb213428e1c37cf7/embed" == SKETCHFAB_EMBED
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            responses: list[tuple[str, int]] = []
            page.on("response", lambda response: responses.append((response.url, response.status)))
            page.goto(f"http://127.0.0.1:{server.server_port}/index.html", wait_until="domcontentloaded")

            section = page.locator("#equipment")
            assert section.count() == 1, "Equipment section must appear once on the homepage"
            assert page.locator('a[href="#equipment"]').count() == 1, "Equipment section anchor is missing"
            root = section.locator("[data-equipment-root]")
            assert root.count() == 1, "Equipment viewer root is missing"
            assert root.locator("[data-equipment-mode]").count() == 2, "2D/3D selector must expose two modes"
            assert root.locator("[data-equipment-angle]").count() == 5, "All five supplied 2D angles must be selectable"
            assert root.locator("[data-camera-model], [data-camera-object], [data-blueprint-view], .equipment-model-3d, .equipment-blueprint").count() == 0, (
                "Retired CSS/3D and SVG schematic models must not remain"
            )
            assert page.locator('script[src*="equipment.js"]').count() == 0, "Retired equipment controller is still loaded"
            assert page.locator('script[src*="equipment-viewer.js"]').count() == 1, "Equipment viewer controller is not loaded"

            photo = root.locator("[data-equipment-photo]")
            assert photo.count() == 1 and photo.is_visible(), "2D product photo panel must be visible by default"
            assert "eos-3000d-angle-sprite.webp" in photo.evaluate("(node) => getComputedStyle(node).backgroundImage")
            assert root.locator('[data-equipment-mode="2d"]').get_attribute("aria-pressed") == "true"
            assert root.locator('[data-equipment-angle="front"]').get_attribute("aria-pressed") == "true"
            assert root.locator("[data-equipment-embed] iframe").count() == 0, "3D iframe should load only on demand"

            for angle in ("flash", "left", "right", "top", "front"):
                button = root.locator(f'[data-equipment-angle="{angle}"]')
                button.click()
                assert button.get_attribute("aria-pressed") == "true", f"{angle} angle state did not update"
                assert photo.get_attribute("data-angle") == angle, f"{angle} photo angle did not update"

            root.locator('[data-equipment-mode="3d"]').click()
            iframe = root.locator("[data-equipment-embed] iframe")
            assert iframe.count() == 1, "Selecting 3D should create the Sketchfab iframe"
            assert iframe.get_attribute("src") == SKETCHFAB_EMBED
            assert iframe.get_attribute("title")
            assert iframe.evaluate("(node) => node.allowFullscreen")
            assert root.locator("[data-equipment-mode='3d']").get_attribute("aria-pressed") == "true"
            assert root.locator("[data-equipment-angles]").is_hidden(), "2D angle controls should hide in 3D mode"

            root.locator('[data-equipment-mode="2d"]').click()
            assert root.locator("[data-equipment-embed]").is_hidden()
            assert root.locator("[data-equipment-angles]").is_visible()
            assert root.locator('[data-equipment-mode="2d"]').get_attribute("aria-pressed") == "true"
            assert iframe.count() == 1, "Returning to 2D should reuse, not duplicate, the existing iframe"

            details = section.inner_text()
            for expected in ("Canon EOS 3000D", "18 MP", "DIGIC 4+", "9-point AF", "Canon EF-S 18–55mm",
                             "Revision-dependent", "lens revision", "Canon EOS 3000"):
                assert expected.lower() in details.lower(), f"Equipment details missing {expected!r}"
            assert SKETCHFAB_MODEL in section.locator('a[href*="sketchfab.com"]').get_attribute("href")

            asset_responses = [status for url, status in responses if "eos-3000d-angle-sprite.webp" in url]
            assert asset_responses and asset_responses[0] == 200, f"2D image sprite failed to load: {asset_responses}"

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
    print("TOKI 2D angle selector, Sketchfab 3D mode, equipment specs, and responsive layout: PASS")


if __name__ == "__main__":
    main()
