#!/usr/bin/env python3
"""Smoke-test mobile WebKit and Android-Chrome emulation plus rendered image integrity."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts" / "qa_support"))
from toki_local_https_server import start_https_server
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
    # The local HTTPS origin must remain reachable after the page's CSP upgrade.
    # Only external third-party HTTPS requests are blocked in these deterministic tests.
    context.route(
        "https://**",
        lambda request: request.continue_()
        if request.request.url.startswith(base_url + "/")
        else request.abort(),
    )
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
    if dimensions["document"] > dimensions["viewport"] + 1:
        offenders = page.evaluate(
            """() => Array.from(document.querySelectorAll("body *")).map((element) => {
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                return {
                    tag: element.tagName.toLowerCase(),
                    id: element.id || "",
                    className: typeof element.className === "string" ? element.className : "",
                    left: Math.round(rect.left * 10) / 10,
                    right: Math.round(rect.right * 10) / 10,
                    width: Math.round(rect.width * 10) / 10,
                    scrollWidth: element.scrollWidth,
                    position: style.position,
                    transform: style.transform,
                    overflowX: style.overflowX,
                    display: style.display
                };
            }).filter(item => item.width > window.innerWidth + 1 ||
                              item.right > window.innerWidth + 1 ||
                              item.left < -window.innerWidth)
              .sort((a, b) => Math.max(b.right - window.innerWidth, b.width - window.innerWidth) -
                              Math.max(a.right - window.innerWidth, a.width - window.innerWidth))
              .slice(0, 30)"""
        )
        stylesheet_state = page.evaluate(
            """() => {
                const brand = document.querySelector(".brand-mark");
                const card = document.querySelector(".gallery-card");
                const grid = document.querySelector(".gallery-grid");
                const describe = element => {
                    if (!element) return null;
                    const style = getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return {
                        rectWidth: Math.round(rect.width * 10) / 10,
                        cssWidth: style.width,
                        maxWidth: style.maxWidth,
                        minWidth: style.minWidth,
                        display: style.display,
                        boxSizing: style.boxSizing,
                        overflowX: style.overflowX
                    };
                };
                return {
                    styleSheetCount: document.styleSheets.length,
                    styleSheets: Array.from(document.styleSheets).map(sheet => ({
                        href: sheet.href,
                        disabled: sheet.disabled
                    })),
                    brand: describe(brand),
                    grid: describe(grid),
                    card: describe(card),
                    root: {
                        width: getComputedStyle(document.documentElement).width,
                        boxSizing: getComputedStyle(document.documentElement).boxSizing
                    }
                };
            }"""
        )
        raise AssertionError(
            f"{label} {route}: horizontal document overflow: {dimensions}; "
            f"largest overflowing elements: {offenders}; "
            f"stylesheet/computed-style diagnostics: {stylesheet_state}"
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

    server, thread, certificate_dir, base_url = start_https_server(partial(QuietHandler))

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
                "ignore_https_errors": True,
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
                "ignore_https_errors": True,
            }
            for route in ROUTES:
                verify_route(chromium, "Chromium/Android-emulation", base_url, route, android_options)
            chromium.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        certificate_dir.cleanup()


if __name__ == "__main__":
    main()
