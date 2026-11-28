#!/usr/bin/env python3
"""Smoke-test mobile WebKit and Android-Chrome emulation plus rendered image integrity."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "dist"
ROUTES = (
    "/",
    "/booking.html",
    "/library.html",
    "/policies.html",
    "/admin.html",
    "/client-gallery.html",
    "/404.html",
)


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, *args):
        pass


def verify_route(browser, label: str, base_url: str, route: str, context_options: dict) -> None:
    context = browser.new_context(**context_options)
    context.route("https://**", lambda request: request.abort())
    page = context.new_page()
    page.set_default_timeout(8_000)
    response = page.goto(base_url + route, wait_until="domcontentloaded")
    assert response is not None and response.status == 200, (
        f"{label} {route}: route did not load (response={response})"
    )
    page.wait_for_load_state("load", timeout=12_000)

    dimensions = page.evaluate(
        """() => ({
            viewport: window.innerWidth,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth
        })"""
    )
    assert dimensions["document"] <= dimensions["viewport"] + 1, (
        f"{label} {route}: horizontal document overflow: {dimensions}"
    )
    assert dimensions["body"] <= dimensions["viewport"] + 1, (
        f"{label} {route}: horizontal body overflow: {dimensions}"
    )

    image_count = page.locator("img").count()
    checked_images = 0
    for index in range(image_count):
        image = page.locator("img").nth(index)
        if not image.is_visible():
            continue
        image.scroll_into_view_if_needed(timeout=3_000)
        handle = image.element_handle()
        assert handle is not None
        page.wait_for_function(
            "(img) => img.complete",
            arg=handle,
            timeout=8_000,
        )
        metrics = image.evaluate(
            """img => ({
                src: img.currentSrc || img.src,
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                loading: img.loading
            })"""
        )
        assert metrics["naturalWidth"] > 0 and metrics["naturalHeight"] > 0, (
            f"{label} {route}: visible image failed to decode: {metrics}"
        )
        checked_images += 1

    print(
        f"PASS {label} {route}: {dimensions['viewport']}px viewport, "
        f"no horizontal overflow, {checked_images}/{image_count} visible images decoded."
    )
    page.close()
    context.close()


def main() -> None:
    assert SITE.is_dir(), f"Packaged site directory is missing: {SITE}"
    for route in ROUTES:
        target = SITE / route.lstrip("/") if route != "/" else SITE / "index.html"
        assert target.is_file() and target.stat().st_size > 0, f"Missing packaged route: {route}"

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            webkit = playwright.webkit.launch(headless=True)
            safari_options = {
                "viewport": {"width": 390, "height": 844},
                "device_scale_factor": 3,
                "is_mobile": True,
                "has_touch": True,
                "user_agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
                    "Mobile/15E148 Safari/604.1"
                ),
                "reduced_motion": "reduce",
            }
            for route in ROUTES:
                verify_route(webkit, "WebKit/iPhone-Safari-emulation", base_url, route, safari_options)
            webkit.close()

            chromium = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            android_options = {
                "viewport": {"width": 412, "height": 915},
                "device_scale_factor": 2.625,
                "is_mobile": True,
                "has_touch": True,
                "user_agent": (
                    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Mobile Safari/537.36"
                ),
                "reduced_motion": "reduce",
            }
            for route in ROUTES:
                verify_route(chromium, "Chromium/Android-emulation", base_url, route, android_options)
            chromium.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
