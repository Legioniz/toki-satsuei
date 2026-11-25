#!/usr/bin/env python3
"""Browser regression checks for TOKI's scroll-linked chapter and parallax system."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "index.html": [".hero-opening", ".work-section", ".about-section", ".contact-section"],
    "library.html": [".archive-head"],
    "policies.html": [".policy-hero", ".policy-article"],
    "admin.html": [".admin-main"],
    "client-gallery.html": [".client-main"],
}


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    motion = (ROOT / "motion-system.js").read_text(encoding="utf-8")
    global_css = (ROOT / "global-motion.css").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

    for token in [
        "SCROLL_SCENE_SELECTOR", "SCROLL_PARALLAX_SELECTOR",
        "--toki-scene-progress", "--toki-scene-position",
        "--toki-parallax-y", "refreshScrollScenes",
    ]:
        assert token in motion, f"Motion engine is missing {token}"
    for token in ["focus-pull", "film-gate", "@keyframes tokiFocusPull", "@keyframes tokiFilmGate"]:
        assert token in global_css, f"Reveal profile is missing {token}"
    for token in [".toki-scene-track", ".toki-scroll-parallax", "prefers-reduced-motion: reduce"]:
        assert token in global_css, f"Global motion layer is missing {token}"
    assert "toki-scroll-motion-qa.py" in workflow, "Scroll motion browser QA is not part of CI."

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
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
                assert page.locator(".toki-scene-track").count() >= len(selectors)
                page.close()

            page = context.new_page()
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.wait_for_selector(".toki-scroll-scene > .toki-scene-track")
            assert page.locator(".toki-scroll-scene").count() >= 10

            # The active chapter marker advances with the document's scroll position.
            work = page.locator(".work-section")
            work.evaluate("""node => {
              document.documentElement.style.scrollBehavior = "auto";
              window.scrollTo(0, window.scrollY + node.getBoundingClientRect().top - innerHeight * 0.38);
            }""")
            page.wait_for_timeout(90)
            first = float(work.evaluate("(node) => node.style.getPropertyValue('--toki-scene-progress')"))
            page.evaluate("window.scrollBy(0, 120)")
            page.wait_for_timeout(90)
            second = float(work.evaluate("(node) => node.style.getPropertyValue('--toki-scene-progress')"))
            assert 0 <= first <= 1 and 0 <= second <= 1 and second > first, (
                f"Chapter progress should advance while scrolling: {first} -> {second}"
            )

            # Photography receives a small, bounded parallax offset as it crosses the viewport.
            about_image = page.locator(".about-visual img")
            about_image.evaluate("""node => {
              window.scrollTo(0, window.scrollY + node.getBoundingClientRect().top - innerHeight * 0.42);
            }""")
            page.wait_for_timeout(90)
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

    print("PASS TOKI scroll motion: chapter progress, parallax bounds, five page integrations, six responsive widths, and reduced-motion parity.")


if __name__ == "__main__":
    main()
