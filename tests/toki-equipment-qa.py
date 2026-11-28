#!/usr/bin/env python3
"""Browser regression checks for the 2D equipment angles and on-demand 3D viewer."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CAMERA_ASSETS = {
    "front": ROOT / "assets" / "equipment" / "camera" / "EOS-3000D-front.png",
    "flash": ROOT / "assets" / "equipment" / "camera" / "EOS-3000D-pop-up-flash.png",
    "left": ROOT / "assets" / "equipment" / "camera" / "EOS-3000D-left-side.png",
    "right": ROOT / "assets" / "equipment" / "camera" / "EOS-3000D-right-side.png",
    "top": ROOT / "assets" / "equipment" / "camera" / "EOS-3000D-top.png",
}
LOGO_ASSET = ROOT / "assets" / "brand" / "Toki-Satsuei-Brushstroke-Emblem.png"


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"Not a PNG file: {path}"
    import struct
    return struct.unpack(">II", header[16:24])
SKETCHFAB_MODEL = "https://sketchfab.com/3d-models/canon-eos-3000-7d57163f3bec464cbb213428e1c37cf7"


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    for angle, asset in CAMERA_ASSETS.items():
        assert asset.is_file() and asset.stat().st_size > 100_000, f"{angle} original camera PNG is missing or incomplete."
        assert png_dimensions(asset) == (362, 320), f"{angle} source dimensions unexpectedly changed."
    assert LOGO_ASSET.is_file() and LOGO_ASSET.stat().st_size > 15_000, "Current TOKI logo asset is missing or incomplete."
    home_markup = (ROOT / "index.html").read_text(encoding="utf-8")
    equipment_markup = home_markup.split('<section class="equipment-section"', 1)[1].split('<section class="faq-section"', 1)[0]
    assert 'id="equipment"' in equipment_markup, "Homepage equipment section is missing its navigation target."
    assert 'data-equipment-root' in equipment_markup, "Current equipment viewer root is missing."
    assert 'equipment-composition--viewer-only' in equipment_markup, "The compact viewer-only equipment layout was not retained."
    assert equipment_markup.count('data-equipment-angle="') == 5, "All five supplied 2D camera angles must remain in the current viewer."
    assert 'data-equipment-mode="2d"' in equipment_markup and 'data-equipment-mode="3d"' in equipment_markup, "The 2D/3D view selector is incomplete."
    assert "Canon EOS 3000D" in equipment_markup and "EF-S 18–55MM" in equipment_markup, "The camera body and standard zoom identification must remain visible."
    assert SKETCHFAB_MODEL in equipment_markup, "The current viewer must retain its linked Sketchfab reference."
    assert "equipment-community-photo" not in equipment_markup, "The retired community-photo panel must not return."
    assert "equipment-spec-panel" not in equipment_markup and "equipment-spec-disclosure" not in equipment_markup, "The retired equipment specification panel must not return."
    logo_png = LOGO_ASSET.read_bytes()
    assert png_dimensions(LOGO_ASSET) == (500, 500), "Current TOKI logo must remain at its submitted 500 × 500 dimensions."
    assert logo_png[25] == 3 and b"tRNS" in logo_png, "Current TOKI logo must retain indexed PNG transparency."
    index_head = (ROOT / "index.html").read_text(encoding="utf-8").split("</head>", 1)[0]
    assert "http-equiv=\"Content-Security-Policy\"" in index_head
    assert "https://sketchfab.com" in index_head, "GitHub Pages must permit the Sketchfab iframe through the page meta policy."
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    csp = next((line for line in headers.splitlines() if "Content-Security-Policy:" in line), "")
    frame_src = next((part.strip() for part in csp.split(";") if part.strip().startswith("frame-src ")), "")
    assert "https://sketchfab.com" in frame_src, (
        "The deployed Content Security Policy must allow the Sketchfab iframe host."
    )
    viewer_source = (ROOT / "src" / "js" / "equipment-viewer.js").read_text(encoding="utf-8")
    assert 'modelUid = "7d57163f3bec464cbb213428e1c37cf7"' in viewer_source, "The Sketchfab controller must initialize the requested model ID."
    assert 'api.setTextureQuality("hd"' in viewer_source, "The Sketchfab controller must request its highest available texture quality."
    assert 'https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js' in viewer_source, "The Sketchfab Viewer API must be loaded for the 3D mode."
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
            assert page.locator('script[src*="assets/js/equipment-viewer.js"]').count() == 1, "Equipment viewer controller is not loaded"

            section.scroll_into_view_if_needed()
            photo = root.locator("[data-equipment-photo]")
            assert photo.count() == 1 and photo.is_visible(), "2D product photo must be visible by default"
            assert photo.evaluate("(node) => node.tagName === 'IMG'"), "Equipment view must use a real image element."
            page.wait_for_function("() => { const image = document.querySelector('[data-equipment-photo]'); return image && image.complete && image.naturalWidth === 362 && image.naturalHeight === 320; }")
            assert photo.get_attribute("src") == "./assets/equipment/camera/EOS-3000D-front.png"
            assert photo.get_attribute("loading") == "eager" and photo.get_attribute("decoding") == "async", "The camera image must be promoted and decoded before the equipment section is displayed."
            assert photo.evaluate("(node) => node.getBoundingClientRect().width <= 362.5"), "Camera PNG must not be enlarged beyond its native width."
            assert root.locator('[data-equipment-mode="2d"]').get_attribute("aria-pressed") == "true"
            assert root.locator('[data-equipment-angle="front"]').get_attribute("aria-pressed") == "true"
            assert root.locator("[data-equipment-embed] iframe").count() == 0, "3D iframe should load only on demand"

            expected_assets = {
                "flash": "EOS-3000D-pop-up-flash.png",
                "left": "EOS-3000D-left-side.png",
                "right": "EOS-3000D-right-side.png",
                "top": "EOS-3000D-top.png",
                "front": "EOS-3000D-front.png",
            }
            for angle in ("flash", "left", "right", "top", "front"):
                button = root.locator(f'[data-equipment-angle="{angle}"]')
                button.click()
                assert button.get_attribute("aria-pressed") == "true", f"{angle} angle state did not update"
                assert photo.get_attribute("data-angle") == angle, f"{angle} photo angle did not update"
                assert photo.get_attribute("src") == "./assets/equipment/camera/" + expected_assets[angle], f"{angle} original camera image did not update"

            root.locator('[data-equipment-mode="3d"]').click()
            iframe = root.locator("[data-equipment-embed] iframe")
            assert iframe.count() == 1, "Selecting 3D should create the Sketchfab iframe"
            assert iframe.get_attribute("src") is None or "sketchfab.com" in iframe.get_attribute("src"), "Sketchfab API iframe source must be assigned by the viewer after initialization."
            assert iframe.get_attribute("title")
            assert iframe.evaluate("(node) => node.allowFullscreen")
            assert root.locator("[data-equipment-mode='3d']").get_attribute("aria-pressed") == "true"
            assert root.locator("[data-equipment-angles]").is_hidden(), "2D angle controls should hide in 3D mode"

            root.locator('[data-equipment-mode="2d"]').click()
            assert root.locator("[data-equipment-embed]").is_hidden()
            assert root.locator("[data-equipment-angles]").is_visible()
            assert root.locator('[data-equipment-mode="2d"]').get_attribute("aria-pressed") == "true"
            assert iframe.count() == 1, "Returning to 2D should reuse, not duplicate, the existing iframe"

            assert section.locator(".equipment-spec-panel, .equipment-spec-disclosure").count() == 0, (
                "The retired specification panel must remain removed from the compact equipment section."
            )
            details = section.inner_text()
            for expected in ("Canon EOS 3000D", "EF-S 18–55MM", "2D PRODUCT PHOTOS", "3D INTERACTIVE MODEL"):
                assert expected.lower() in details.lower(), f"Current equipment viewer is missing {expected!r}"
            assert SKETCHFAB_MODEL in section.locator('a[href*="sketchfab.com"]').get_attribute("href")

            asset_responses = [(url, status) for url, status in responses if "/assets/equipment/camera/" in url]
            assert any(url.endswith("EOS-3000D-front.png") and status == 200 for url, status in asset_responses), (
                f"Original camera PNG failed to load: {asset_responses}"
            )

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
