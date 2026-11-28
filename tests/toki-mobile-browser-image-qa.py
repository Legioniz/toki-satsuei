#!/usr/bin/env python3
"""Smoke-test mobile WebKit and Android-Chrome emulation plus rendered image integrity."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
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
    image_requests: list[str] = []
    image_responses: list[str] = []
    failed_image_requests: list[str] = []

    def is_image_url(url: str) -> bool:
        return any(
            url.lower().split("?", 1)[0].endswith(extension)
            for extension in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")
        )

    page.on(
        "request",
        lambda request: image_requests.append(request.url) if is_image_url(request.url) else None,
    )
    page.on(
        "response",
        lambda response: image_responses.append(f"{response.status} {response.url}")
        if is_image_url(response.url) else None,
    )
    page.on(
        "requestfailed",
        lambda request: failed_image_requests.append(request.url)
        if is_image_url(request.url) else None,
    )
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
    forced_eager_images = 0
    skipped_external_images: list[str] = []
    for index in range(image_count):
        image = page.locator("img").nth(index)
        if not image.is_visible():
            continue
        # Center the image, rather than accepting a one-pixel intersection at the
        # viewport edge. WebKit can otherwise leave loading="lazy" pending even
        # though Playwright considers the image visible.
        image.evaluate(
            """img => img.scrollIntoView({
                block: "center",
                inline: "nearest",
                behavior: "instant"
            })"""
        )
        handle = image.element_handle()
        assert handle is not None
        candidate_url = image.evaluate("(img) => img.currentSrc || img.src")
        if not candidate_url.startswith(base_url + "/"):
            # This deterministic test context deliberately aborts all off-origin
            # HTTPS requests. Report those references separately instead of treating
            # an intentionally blocked third-party image as a failed local asset.
            skipped_external_images.append(candidate_url)
            continue
        declared_loading = image.get_attribute("loading") or "auto"
        forced_eager_for_decode = False
        try:
            page.wait_for_function(
                "(img) => img.complete",
                arg=handle,
                timeout=4_000,
            )
        except PlaywrightTimeoutError as lazy_timeout:
            if declared_loading == "lazy":
                # WebKit's headless iPhone emulation can leave native lazy images
                # pending after scrollIntoView even when the image is centered.
                # Preserve and report the original lazy declaration, then force only
                # this in-view element eager inside the test page to verify the real
                # same-origin responsive asset can be fetched and decoded.
                image.evaluate("(img) => { img.loading = 'eager'; }")
                forced_eager_for_decode = True
                print(
                    f"WARN {label} {route}: WebKit did not start native lazy fetch "
                    f"for image {index + 1}/{image_count} after scrolling it into view; "
                    "forcing eager only in the isolated test context for decode verification."
                )
                try:
                    page.wait_for_function(
                        "(img) => img.complete",
                        arg=handle,
                        timeout=15_000,
                    )
                except PlaywrightTimeoutError as eager_timeout:
                    stalled = image.evaluate(
                        """img => ({
                            src: img.src,
                            currentSrc: img.currentSrc,
                            complete: img.complete,
                            naturalWidth: img.naturalWidth,
                            naturalHeight: img.naturalHeight,
                            loading: img.loading,
                            decoding: img.decoding,
                            rect: (() => {
                                const r = img.getBoundingClientRect();
                                return {top:r.top,bottom:r.bottom,width:r.width,height:r.height};
                            })(),
                            scrollY: window.scrollY
                        })"""
                    )
                    raise AssertionError(
                        f"{label} {route}: forced-eager image {index + 1}/{image_count} "
                        f"did not finish loading: {stalled}; image requests: {image_requests}; "
                        f"responses: {image_responses}; failed requests: {failed_image_requests}"
                    ) from eager_timeout
            else:
                stalled = image.evaluate(
                    """img => ({
                        src: img.src,
                        currentSrc: img.currentSrc,
                        complete: img.complete,
                        naturalWidth: img.naturalWidth,
                        naturalHeight: img.naturalHeight,
                        loading: img.loading,
                        decoding: img.decoding,
                        rect: (() => {
                            const r = img.getBoundingClientRect();
                            return {top:r.top,bottom:r.bottom,width:r.width,height:r.height};
                        })(),
                        scrollY: window.scrollY
                    })"""
                )
                raise AssertionError(
                    f"{label} {route}: non-lazy image {index + 1}/{image_count} "
                    f"did not finish loading after scrolling: {stalled}; image requests: "
                    f"{image_requests}; responses: {image_responses}; "
                    f"failed requests: {failed_image_requests}"
                ) from lazy_timeout
        metrics = image.evaluate(
            """(img, originalLoading) => ({
                src: img.currentSrc || img.src,
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                declaredLoading: originalLoading,
                testLoading: img.loading,
                decoding: img.decoding
            })""",
            declared_loading,
        )
        metrics["forcedEagerForDecode"] = forced_eager_for_decode
        assert metrics["naturalWidth"] > 0 and metrics["naturalHeight"] > 0, (
            f"{label} {route}: visible image failed to decode: {metrics}"
        )
        checked_images += 1
        forced_eager_images += int(forced_eager_for_decode)

    print(
        f"PASS {label} {route}: {dimensions['viewport']}px viewport, "
        f"no horizontal overflow, {checked_images} same-origin images decoded; "
        f"{len(skipped_external_images)} off-origin image(s) reported separately; "
        f"{forced_eager_images} WebKit lazy-load fallbacks in test context."
    )
    if skipped_external_images:
        print(f"INFO {label} {route}: off-origin images not fetched by the isolated test policy: "
              f"{skipped_external_images}")
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
