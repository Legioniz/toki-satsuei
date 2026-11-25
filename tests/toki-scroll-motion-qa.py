#!/usr/bin/env python3
"""Browser regression checks for TOKI's scroll-linked chapter and parallax system."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "index.html": [".hero-opening", ".work-section", ".about-section", ".contact-section"],
    "library.html": [".archive-head"],
    "policies.html": [".policy-hero", ".policy-article"],
    "admin.html": [".admin-main"],
    "client-gallery.html": [".client-main"],
    "404.html": [".not-found-main"],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    motion = (ROOT / "motion-system.js").read_text(encoding="utf-8")
    global_css = (ROOT / "global-motion.css").read_text(encoding="utf-8")
    shared_motion_css = (ROOT / "motion-refinements.css").read_text(encoding="utf-8")
    intro_css = (ROOT / "motion-system.css").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    archive_script = (ROOT / "library.js").read_text(encoding="utf-8")

    intro_timing = re.search(
        r"animation:\s*tokiIntroCurtainOut\s+([0-9.]+)s\s+var\(--ease-quart-in-out\)\s+([0-9.]+)s\s+forwards",
        intro_css,
    )
    assert intro_timing, "Page intro curtain is missing its explicit timing."
    intro_total = sum(float(value) for value in intro_timing.groups())
    assert intro_total <= 0.6, (
        f"Page intro curtain should clear in 600ms or less, found {intro_total:.3f}s."
    )
    intro_fallback = re.search(r"window\.setTimeout\(cleanup,\s*(\d+)\)", motion)
    assert intro_fallback and int(intro_fallback.group(1)) <= 900, (
        "Page intro fallback cleanup must not hold the overlay longer than 900ms."
    )

    for token in [
        "SCROLL_SCENE_SELECTOR", "SCROLL_PARALLAX_SELECTOR",
        "--toki-scene-progress", "--toki-scene-position",
        "--toki-parallax-y", "--toki-scene-focus", "is-scene-active",
        "data-scroll-direction", "refreshScrollScenes",
    ]:
        assert token in motion, f"Motion engine is missing {token}"
    for token in ["refreshScrollTargets", "scrollScenes", "scrollTracked", "scrollParallax"]:
        assert token in motion, f"Scroll engine is missing cached target registry: {token}"
    for token in [
        "document.startViewTransition", "toki-album-container",
        "clearAlbumViewTransitionNames", "reducedMotion",
    ]:
        assert token in archive_script, f"Archive container transition is missing {token}"
    assert "::view-transition-group(toki-album-container)" in shared_motion_css, (
        "Shared album container transition timing is missing."
    )
    for token in ["focus-pull", "film-gate", "@keyframes tokiFocusPull", "@keyframes tokiFilmGate"]:
        assert token in global_css, f"Reveal profile is missing {token}"
    for token in [".toki-scene-track", ".toki-scroll-parallax", "prefers-reduced-motion: reduce"]:
        assert token in global_css, f"Global motion layer is missing {token}"
    for token in [".is-scene-active", "::view-transition-new(root)", "tokiPageEnter", "data-motion-tier"]:
        assert token in shared_motion_css, f"Shared motion refinements are missing {token}"
    assert "toki-scroll-motion-qa.py" in workflow, "Scroll motion browser QA is not part of CI."
    shared_asset_versions = set()
    for page_name in ["index.html", "library.html", "policies.html", "404.html", "admin.html", "client-gallery.html"]:
        page_source = (ROOT / page_name).read_text(encoding="utf-8")
        bundle = {
            "index.html": "toki-home.css",
            "library.html": "toki-archive.css",
            "policies.html": "toki-policies.css",
            "404.html": "toki-404.css",
            "admin.html": "toki-admin.css",
            "client-gallery.html": "toki-client.css",
        }[page_name]
        css_version = re.search(rf'href="./{re.escape(bundle)}\?v=([^"]+)"', page_source)
        motion_version = re.search(r'src="./motion-system\.js\?v=([^"]+)"', page_source)
        assert css_version and motion_version, f"{page_name}: shared motion asset cache key is missing"
        assert css_version.group(1) == motion_version.group(1), (
            f"{page_name}: stylesheet and motion controller cache keys are out of sync"
        )
        shared_asset_versions.add(css_version.group(1))
    assert len(shared_asset_versions) == 1, (
        "Page bundles and the shared motion controller must use one coordinated cache version."
    )


    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                reduced_motion="no-preference",
            )
            context.route("https://**", lambda route: route.abort())

            for filename, selectors in PAGES.items():
                page = context.new_page()
                page.goto(base + "/" + filename, wait_until="domcontentloaded")
                for selector in selectors:
                    page.locator(selector).first.wait_for(state="attached")
                    scene = page.locator(selector).first
                    assert scene.evaluate("(node) => node.classList.contains('toki-scroll-scene')"), (
                        f"{filename}: {selector} was not registered as a scroll scene"
                    )
                    assert scene.locator(":scope > .toki-scene-track").count() == 1, (
                        f"{filename}: {selector} is missing its focus rail"
                    )
                    assert not scene.locator(":scope > .toki-scene-track").evaluate(
                        "(node) => node.classList.contains('motion-item')"
                    ), f"{filename}: decorative focus rail must not enter the content reveal system"
                assert page.locator(".toki-scene-track").count() >= len(selectors)
                page.close()

            page = context.new_page()
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.wait_for_selector(".toki-scroll-scene > .toki-scene-track")
            assert page.evaluate("window.TokiMotion.reduced") is False, (
                "Normal-motion scroll regression context unexpectedly has reduced motion enabled."
            )
            assert page.locator(".toki-scroll-scene").count() >= 10

            # Chapter progress is updated after a real document scroll.
            work = page.locator(".work-section")
            initial_scroll = page.evaluate("window.scrollY")
            target_scroll = work.evaluate("""node => Math.min(
              document.documentElement.scrollHeight - innerHeight,
              Math.max(0, window.scrollY + node.getBoundingClientRect().top - innerHeight * 0.38)
            )""")
            page.evaluate("""target => {
              const scroller = document.scrollingElement;
              scroller.style.setProperty("scroll-behavior", "auto", "important");
              scroller.scrollTop = target;
              window.TokiMotion.refreshScrollScenes();
            }""", target_scroll)
            page.wait_for_timeout(40)
            first_scroll = page.evaluate("window.scrollY")
            first = float(work.evaluate("(node) => node.style.getPropertyValue('--toki-scene-progress')"))
            page.evaluate("""() => {
              document.scrollingElement.scrollTop += 120;
              window.TokiMotion.refreshScrollScenes();
            }""")
            page.wait_for_timeout(40)
            second_scroll = page.evaluate("window.scrollY")
            second = float(work.evaluate("(node) => node.style.getPropertyValue('--toki-scene-progress')"))
            assert first_scroll > initial_scroll and second_scroll > first_scroll, (
                f"Browser did not advance its scroll position: {initial_scroll} -> {first_scroll} -> {second_scroll}"
            )
            assert 0 <= first <= 1 and 0 <= second <= 1 and second > first, (
                f"Chapter progress should advance while scrolling: {first} -> {second}"
            )

            # Photography receives a small, bounded parallax offset as it crosses the viewport.
            about_image = page.locator(".about-visual img")
            parallax_scroll = about_image.evaluate("""node => Math.min(
              document.documentElement.scrollHeight - innerHeight,
              Math.max(0, window.scrollY + node.getBoundingClientRect().top - innerHeight * 0.42)
            )""")
            page.evaluate("""target => {
              document.scrollingElement.scrollTop = target;
              window.TokiMotion.refreshScrollScenes();
            }""", parallax_scroll)
            page.wait_for_timeout(40)
            parallax = about_image.evaluate("(node) => node.style.getPropertyValue('--toki-parallax-y')")
            assert parallax.endswith("px"), f"About image did not receive scroll parallax: {parallax}"
            assert abs(float(parallax.removesuffix("px"))) <= 16, f"Parallax exceeded its motion budget: {parallax}"

            for width in [320, 390, 680, 768, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 850})
                page.wait_for_timeout(30)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                    f"Horizontal overflow after motion setup at {width}px"
                )

            reduced_context = browser.new_context(
                viewport={"width": 390, "height": 844},
                reduced_motion="reduce",
            )
            reduced_context.route("https://**", lambda route: route.abort())
            reduced_page = reduced_context.new_page()
            reduced_page.goto(base + "/index.html", wait_until="domcontentloaded")
            reduced_track = reduced_page.locator(".toki-scene-track").first
            reduced_track.wait_for(state="attached")
            assert reduced_track.evaluate("(node) => getComputedStyle(node).display === 'none'"), (
                "Scroll chapter graphics must be hidden for reduced-motion users."
            )
            assert reduced_page.evaluate("window.TokiMotion.reduced") is True
            reduced_context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("PASS TOKI scroll motion: chapter focus, progress, parallax bounds, six page integrations, six responsive widths, reduced-motion parity, and cross-page transitions.")


if __name__ == "__main__":
    main()
