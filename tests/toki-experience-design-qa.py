#!/usr/bin/env python3
"""Browser checks for the TOKI SATSUEI experience-design layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    pages = ["index.html", "library.html", "policies.html", "404.html"]
    for filename in pages:
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert "experience.css?v=" in source, f"{filename}: experience layer is not loaded"

    css = (ROOT / "experience.css").read_text(encoding="utf-8")
    for selector in [
        ".booking-form-intro", ".booking-fieldset", ".booking-expectation",
        ".inquiry-form .booking-consent", ".calendar-controls button",
        ".primary-nav a", ".hero-opening .hero-lead",
    ]:
        assert selector in css, f"Experience layer is missing {selector}"

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert home.count('<fieldset class="booking-fieldset">') == 3
    assert "A request is not a reservation" in home
    assert "at least one minute ahead" in home
    assert 'name="preferred_time"' in home and 'step="60"' in home
    assert 'href="#availability"' in home

    site = (ROOT / "site.js").read_text(encoding="utf-8")
    edge = (ROOT / "supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
    assert "function manilaNow()" in site and "preferredTime.min" in site
    assert "function manilaNow()" in edge
    assert "(preferredDate !== now.date || preferredTime > now.time)" in edge

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("https://**", lambda route: route.abort())
            page = context.new_page()
            page.goto(base + "/index.html", wait_until="domcontentloaded")
            page.wait_for_selector(".booking-fieldset")
            assert page.locator(".booking-fieldset").count() == 3
            legends = [" ".join(value.split()) for value in page.locator(".booking-fieldset legend").all_inner_texts()]
            assert legends == ["01 SESSION DETAILS", "02 DATE & PLACE", "03 CONTACT & NOTES"], legends
            assert page.locator(".primary-nav a").count() == 7
            assert page.locator(".booking-expectation").is_visible()

            for selector in [
                'input[name="name"]', 'select[name="session"]',
                'input[name="preferred_date"]', 'input[name="preferred_time"]',
                'input[name="contact_value"]', 'textarea[name="notes"]',
            ]:
                height = page.locator(selector).evaluate("(node) => node.getBoundingClientRect().height")
                assert height >= 44, f"{selector} is below the 44px control target: {height}"

            date_input = page.locator('input[name="preferred_date"]')
            time_input = page.locator('input[name="preferred_time"]')
            today = datetime.now(ZoneInfo("Asia/Manila")).date().isoformat()
            date_input.fill(today)
            date_input.dispatch_event("change")
            minimum = time_input.get_attribute("min")
            assert minimum and len(minimum) == 5 and minimum[2] == ":", f"Invalid same-day minimum: {minimum}"
            time_input.fill("00:00")
            assert time_input.evaluate("(node) => node.validity.rangeUnderflow || node.validity.customError"), \
                "Past same-day time was not blocked in the browser"

            future_date = (datetime.now(ZoneInfo("Asia/Manila")).date() + timedelta(days=2)).isoformat()
            date_input.fill(future_date)
            date_input.dispatch_event("change")
            assert time_input.get_attribute("min") == "00:00", "Future dates should permit any time of day"

            contrast = page.locator(".inquiry-form").evaluate("""form => {
              const panel = form.closest(".contact-panel");
              const label = form.querySelector("label");
              const input = form.querySelector('input[name="name"]');
              const luminance = value => {
                const rgb = value.match(/[0-9.]+/g).slice(0, 3).map(Number).map(v => v / 255);
                const channels = rgb.map(v => v <= .04045 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4));
                return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
              };
              const ratio = (a,b) => {
                const values = [luminance(a),luminance(b)].sort((x,y)=>y-x);
                return (values[0]+.05)/(values[1]+.05);
              };
              return {
                label: ratio(getComputedStyle(label).color, getComputedStyle(panel).backgroundColor),
                input: ratio(getComputedStyle(input).color, getComputedStyle(input).backgroundColor)
              };
            }""")
            assert contrast["label"] >= 4.5, f"Form labels miss 4.5:1 contrast: {contrast}"
            assert contrast["input"] >= 4.5, f"Form input text misses 4.5:1 contrast: {contrast}"

            page.set_viewport_size({"width": 320, "height": 700})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow at 320px"
            page.locator(".menu-toggle").click()
            assert page.locator(".menu-toggle").get_attribute("aria-expanded") == "true"
            assert page.locator(".primary-nav").is_visible()
            page.keyboard.press("Escape")
            assert page.locator(".menu-toggle").get_attribute("aria-expanded") == "false"
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    print("PASS TOKI experience design: grouped booking, same-day limits, readable controls, contrast, and responsive navigation.")


if __name__ == "__main__":
    main()
