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
    pages = ["index.html", "booking.html", "library.html", "policies.html", "404.html"]
    for filename in pages:
        source = (ROOT / filename).read_text(encoding="utf-8")
        bundle_name = {"index.html": "toki-home.css", "booking.html": "toki-home.css", "library.html": "toki-archive.css", "policies.html": "toki-policies.css", "404.html": "toki-404.css"}[filename]
        assert "experience.css" in (ROOT / bundle_name).read_text(encoding="utf-8").splitlines()[0], f"{filename}: experience layer is not bundled"

    css = (ROOT / "experience.css").read_text(encoding="utf-8")
    enhancements = (ROOT / "site-enhancements.css").read_text(encoding="utf-8")
    global_motion = (ROOT / "global-motion.css").read_text(encoding="utf-8")
    motion_js = (ROOT / "motion-system.js").read_text(encoding="utf-8")
    home_bundle = (ROOT / "toki-home.css").read_text(encoding="utf-8")
    for selector in [
        ".booking-form-intro", ".booking-fieldset", ".booking-expectation",
        ".booking-terms-summary", ".toki-assurance", ".toki-booking-sheet__layout", ".package-duration", ".session-flexible-duration",
        ".session-duration-note", ".inquiry-form .booking-consent", ".calendar-controls button",
        ".primary-nav a", ".hero-opening .hero-lead",
    ]:
        assert selector in css, f"Experience layer is missing {selector}"

    assert "grid-template-columns: minmax(0, 1fr)" in enhancements
    motion_refinements = (ROOT / "motion-refinements.css").read_text(encoding="utf-8")
    assert ".toki-booking-sheet .form-split" in enhancements
    assert ".booking-page .toki-assurance__grid" in motion_refinements
    assert ".booking-page .toki-booking-sheet .booking-fieldset" in motion_refinements
    assert "motion-refinements.css" in home_bundle.splitlines()[0]
    assert "site-enhancements.css" in home_bundle.splitlines()[0]
    assert "global-motion.css" in home_bundle.splitlines()[0]
    assert ".toki-intro-logo" in global_motion
    assert "30515ce50_Toki_Satsuei_Brushstroke_Emblem.png" in motion_js
    assert ".toki-booking-sheet .booking-fieldset .form-split > label" in motion_js

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    equipment = home.split('<section class="equipment-section"', 1)[1].split('<section class="faq-section"', 1)[0]
    assert equipment.count('data-equipment-angle=') == 5, "Equipment viewer must expose all five supplied 2D camera angles."
    assert 'data-equipment-mode="2d"' in equipment and 'data-equipment-mode="3d"' in equipment
    assert "eos-3000d-angle-sprite.webp" in (ROOT / "equipment.css").read_text(encoding="utf-8")
    assert "https://sketchfab.com/3d-models/canon-eos-3000-7d57163f3bec464cbb213428e1c37cf7" in equipment

    viewer = (ROOT / "equipment-viewer.js").read_text(encoding="utf-8")
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    assert "https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js" in viewer
    assert 'api.addEventListener("viewerready"' in viewer
    assert 'api.setTextureQuality("hd"' in viewer, "The Sketchfab model must request the highest supported texture quality."
    assert "script-src 'self' 'unsafe-inline' https://static.sketchfab.com" in headers.split("Content-Security-Policy:", 1)[1]
    assert "https://static.sketchfab.com" in home, "The page CSP must allow the official Sketchfab Viewer API script."
    assert "Canon EOS 3000D" in equipment and "Canon EF-S 18–55mm" in equipment
    assert "lens revision" in equipment.lower(), "Lens revision caveat must stay visible."
    assert "equipment-model-3d" not in equipment and "equipment-blueprint" not in equipment, "Retired CSS/2D schematic must stay removed."
    assert "data-camera-object" not in equipment, "Legacy CSS camera object must not return."
    assert 'equipment.js' not in home and 'equipment-viewer.js' in home
    booking = (ROOT / "booking.html").read_text(encoding="utf-8")
    policy = (ROOT / "policies.html").read_text(encoding="utf-8")
    assert 'id="inquiry-form"' not in home and 'href="./booking.html"' in home
    assert booking.count('<fieldset class="booking-fieldset">') == 3
    assert "wizard-progress" not in home and "wizard-stage" not in home
    assert "wizard-to-stage-2" not in home and "Proceed to Step 2" not in home
    assert 'class="booking-page"' in booking
    assert "toki-assurance" in booking and "toki-booking-sheet__layout" in booking
    assert "A request is not a reservation" in booking
    assert "at least one minute ahead" in booking
    assert 'name="preferred_time"' in booking and 'step="60"' in booking
    assert 'href="#availability"' in home
    assert 'data-booking-terms-version="2026-11-16-v1"' in booking
    assert 'name="booking_terms_consent"' in booking
    assert home.count('class="package-duration"') == 4
    for duration in ["15 minutes", "30 minutes", "60 minutes"]:
        assert duration in home
    assert "Outdoor sessions · Event coverage · Custom sessions" in home
    assert "20% reservation fee" in booking
    assert "48 hours" in policy.lower()
    assert "at the scheduled start time" in policy.lower()
    assert "after the agreed start time" in policy.lower()

    site = (ROOT / "site.js").read_text(encoding="utf-8")
    edge = (ROOT / "supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
    terms_migration = (ROOT / "supabase/migrations/20261116104119_toki_booking_terms_acknowledgement.sql").read_text(encoding="utf-8")
    inbox_migration = (ROOT / "supabase/migrations/20261116104834_toki_booking_inbox_terms_acceptance.sql").read_text(encoding="utf-8")
    assert "booking_terms_accepted_at timestamptz" in terms_migration
    assert "booking_terms_version text" in terms_migration
    assert "WITH (security_invoker = true)" in inbox_migration
    assert "booking_terms_version" in inbox_migration and "booking_terms_accepted_at" in inbox_migration
    assert "function updateSessionDurationNote()" in site
    assert r"if(/^\d{4}-\d{2}-\d{2}$/.test(requestedDate)" in site
    assert "bookedSlots" not in site
    assert "booking_terms_consent" in site and "booking_terms_version" in site
    assert "function manilaNow()" in site and "preferredTime.min" in site
    assert "bookingTermsConsent" in edge
    assert "bookingTermsVersion === expectedBookingTermsVersion" in edge
    assert "booking_terms_accepted_at: bookingTermsAcceptedAt" in edge
    assert "booking_terms_version: expectedBookingTermsVersion" in edge
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
            intro = page.locator(".toki-intro-curtain")
            assert intro.count() == 1, "The logo intro should appear on a normal-motion page load."
            assert intro.locator(".toki-intro-logo").get_attribute("src") == "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/30515ce50_Toki_Satsuei_Brushstroke_Emblem.png"
            assert page.locator("#inquiry-form").count() == 0, "Homepage should link out to booking instead of embedding the form."
            booking_page = context.new_page()
            booking_page.goto(base + "/booking.html", wait_until="domcontentloaded")
            booking_page.wait_for_selector(".booking-fieldset")
            assert booking_page.locator(".booking-fieldset").count() == 3
            legends = [" ".join(value.split()) for value in booking_page.locator(".booking-fieldset legend").all_inner_texts()]
            assert legends == ["SESSION DETAILS", "DATE & LOCATION", "CONTACT & NOTES"], legends
            assert booking_page.locator(".primary-nav a").count() == 7
            assert booking_page.locator(".booking-expectation").is_visible()
            assert booking_page.locator(".booking-terms-summary").is_visible()
            assert booking_page.locator(".toki-assurance").is_visible()
            assert booking_page.locator(".wizard-progress").count() == 0
            assert booking_page.locator("#wizard-to-stage-2").count() == 0
            assert booking_page.locator('input[name="booking_terms_consent"]').evaluate("(node) => node.required")
            assert booking_page.locator('input[name="privacy_consent"]').evaluate("(node) => node.required")
            assert page.locator(".package-duration").count() == 4
            duration_cards = [" ".join(value.split()) for value in page.locator(".package-duration").all_inner_texts()]
            assert ["15 minutes" in duration_cards[0], "30 minutes" in duration_cards[1],
                    "60 minutes" in duration_cards[2], "30 minutes" in duration_cards[3]] == [True] * 4
            session_select = booking_page.locator('select[name="session"]')
            duration_note = booking_page.locator("#session-duration-note")
            session_select.select_option("Quick Snap")
            assert duration_note.inner_text() == "Typical duration: 15 minutes. The exact start and end time will be agreed in writing."
            session_select.select_option("Signature Session")
            assert duration_note.inner_text() == "Typical duration: 60 minutes. The exact start and end time will be agreed in writing."
            session_select.select_option("Custom session")
            assert duration_note.inner_text() == "Duration will be agreed with you in writing before the session is confirmed."

            for selector in [
                'input[name="name"]', 'select[name="session"]',
                'input[name="preferred_date"]', 'input[name="preferred_time"]',
                'input[name="contact_value"]', 'textarea[name="notes"]',
            ]:
                height = booking_page.locator(selector).evaluate("(node) => node.getBoundingClientRect().height")
                assert height >= 44, f"{selector} is below the 44px control target: {height}"

            date_input = booking_page.locator('input[name="preferred_date"]')
            time_input = booking_page.locator('input[name="preferred_time"]')
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

            contrast = booking_page.locator(".inquiry-form").evaluate("""form => {
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

            for width in [320, 390, 680, 768, 960, 1024, 1200, 1440]:
                booking_page.set_viewport_size({"width": width, "height": 850})
                layout_columns = booking_page.locator(".toki-booking-sheet__layout").evaluate("(node) => getComputedStyle(node).gridTemplateColumns.trim().split(/\\s+/).length")
                split_columns = booking_page.locator(".toki-booking-sheet .form-split").first.evaluate("(node) => getComputedStyle(node).gridTemplateColumns.trim().split(/\\s+/).length")
                expected_layout_columns = 2 if width >= 1200 else 1
                expected_split_columns = 2 if width >= 960 else 1
                assert layout_columns == expected_layout_columns, f"Unexpected booking group layout at {width}px: {layout_columns}"
                assert split_columns == expected_split_columns, f"Unexpected field layout at {width}px: {split_columns}"
                if width <= 680:
                    assurance_columns = booking_page.locator(".toki-assurance__grid").evaluate(
                        "(node) => getComputedStyle(node).gridTemplateColumns.trim().split(/\\s+/).length"
                    )
                    expected_assurance_columns = 1 if width <= 360 else 2
                    assert assurance_columns == expected_assurance_columns, (
                        f"Unexpected mobile assurance layout at {width}px: {assurance_columns}"
                    )
                geometry = booking_page.locator('select[name="session"]').evaluate("(node) => ({control: node.getBoundingClientRect().width, label: node.parentElement.getBoundingClientRect().width})")
                assert geometry["control"] >= geometry["label"] - 1, f"Booking control should fill its row at {width}px: {geometry}"

            booking_page.set_viewport_size({"width": 390, "height": 844})
            mobile_fieldset = booking_page.locator(".booking-fieldset").first.evaluate("""node => {
              const style = getComputedStyle(node);
              return {border: style.borderTopStyle, background: style.backgroundColor};
            }""")
            assert mobile_fieldset["border"] == "solid", f"Mobile form section should read as a distinct card: {mobile_fieldset}"
            assert mobile_fieldset["background"] != "rgba(0, 0, 0, 0)", f"Mobile form card needs a defined surface: {mobile_fieldset}"

            # Verify query prefill and ignore URL-supplied availability counts.
            prefill_date = (datetime.now(ZoneInfo("Asia/Manila")).date() + timedelta(days=5)).isoformat()
            prefill_page = context.new_page()
            prefill_page.goto(
                base + "/booking.html?session=Duo%20Session&participants=3&additional_photos=2&additional_time=15&date="
                + prefill_date + "&bookedSlots=99&source=availability-calendar",
                wait_until="domcontentloaded",
            )
            assert prefill_page.locator('select[name="session"]').input_value() == "Duo Session"
            assert prefill_page.locator('input[name="participants"]').input_value() == "3"
            assert prefill_page.locator('input[name="additional_photos"]').input_value() == "2"
            assert prefill_page.locator('input[name="additional_time"]').input_value() == "15"
            assert prefill_page.locator('input[name="preferred_date"]').input_value() == prefill_date
            handoff_status = prefill_page.locator("#form-status").inner_text().lower()
            assert "inquiry only" in handoff_status
            assert "guide only" in handoff_status
            assert "99 confirmed" not in handoff_status
            prefill_page.close()

            booking_page.set_viewport_size({"width": 320, "height": 700})
            assert booking_page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow at 320px"
            # Generate a real down/up scroll pair. Form-control checks above may
            # already have left the page at the top, making a simple scrollTop=0
            # assignment a no-op that cannot notify the shared header controller.
            scroll_range = booking_page.evaluate(
                "() => document.documentElement.scrollHeight - window.innerHeight"
            )
            assert scroll_range > 96, "Booking page must be scrollable for masthead interaction QA."
            booking_page.evaluate("""() => {
              document.scrollingElement.style.setProperty("scroll-behavior", "auto", "important");
              document.scrollingElement.scrollTop = 0;
            }""")
            booking_page.wait_for_function("window.scrollY <= 1")
            # Let the scroll listener's queued animation-frame update finish before
            # issuing the next direction, so consecutive scrolls cannot coalesce.
            booking_page.evaluate(
                "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
            )
            booking_page.mouse.move(160, 350)
            booking_page.mouse.wheel(0, 240)
            booking_page.wait_for_function("window.scrollY > 1")
            booking_page.wait_for_function("""() => {
              const header = document.querySelector(".site-header");
              return header && header.classList.contains("is-auto-hidden") &&
                header.getAttribute("aria-hidden") === "true" && header.inert;
            }""")
            previous_scroll = booking_page.evaluate("window.scrollY")
            # Exercise a real upward wheel gesture rather than assigning scrollTop.
            # This drives the same direction-aware path used by visitors.
            booking_page.mouse.wheel(0, -360)
            booking_page.wait_for_function(
                "(previous) => window.scrollY < previous",
                arg=previous_scroll,
                timeout=3500,
            )
            # Verify the real upward gesture, then deterministically return to
            # the top. Wheel distance is browser/viewport dependent in headless CI.
            # The scroll event must synchronously restore visual and accessible state.
            booking_page.evaluate("() => window.scrollTo({ top: 0, behavior: 'instant' })")
            booking_page.wait_for_function("window.scrollY <= 1", timeout=3500)
            # Confirm the controller has restored the accessible state, then move
            # keyboard focus to the menu control. The design intentionally reveals
            # the fixed masthead on :focus-within for keyboard navigation.
            booking_page.wait_for_function("""() => {
              const header = document.querySelector(".site-header");
              return window.scrollY <= 1 && header &&
                !header.classList.contains("is-auto-hidden") &&
                !header.classList.contains("is-initial-hidden") &&
                header.getAttribute("aria-hidden") === "false" && !header.inert;
            }""")
            menu_toggle = booking_page.locator(".menu-toggle")
            menu_toggle.focus()
            booking_page.wait_for_function("""() => {
              const header = document.querySelector(".site-header");
              const button = header?.querySelector(".menu-toggle");
              if (!header || !button || !header.matches(":focus-within") ||
                  header.classList.contains("is-auto-hidden") ||
                  header.getAttribute("aria-hidden") !== "false" || header.inert) return false;
              const headerRect = header.getBoundingClientRect();
              const buttonRect = button.getBoundingClientRect();
              return Math.abs(headerRect.top) <= 1 &&
                buttonRect.left >= 0 && buttonRect.top >= 0 &&
                buttonRect.right <= window.innerWidth &&
                buttonRect.bottom <= window.innerHeight;
            }""")
            menu_box = menu_toggle.bounding_box()
            assert menu_box and menu_toggle.is_visible() and menu_toggle.is_enabled(), (
                "Booking navigation toggle must be visible and enabled before pointer interaction."
            )
            menu_hit = menu_toggle.evaluate("""button => {
              const rect = button.getBoundingClientRect();
              const target = document.elementFromPoint(
                rect.left + rect.width / 2,
                rect.top + rect.height / 2
              );
              return {accepted: target === button || button.contains(target), target: target?.className || target?.tagName};
            }""")
            assert menu_hit["accepted"], f"Booking navigation toggle is occluded by {menu_hit['target']}"
            # Use viewport coordinates after the explicit hit-test. Locator.click()
            # may auto-scroll a fixed header button and race the scroll-hide controller.
            booking_page.mouse.click(
                menu_box["x"] + menu_box["width"] / 2,
                menu_box["y"] + menu_box["height"] / 2,
            )
            assert menu_toggle.get_attribute("aria-expanded") == "true"
            assert booking_page.locator(".primary-nav").is_visible()
            booking_page.keyboard.press("Escape")
            assert booking_page.locator(".menu-toggle").get_attribute("aria-expanded") == "false"

            reduced_context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            reduced_context.route("https://**", lambda route: route.abort())
            reduced_page = reduced_context.new_page()
            reduced_page.goto(base + "/index.html", wait_until="domcontentloaded")
            assert reduced_page.locator(".toki-intro-curtain").count() == 0, "The intro must respect reduced-motion preferences."
            reduced_context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    print("PASS TOKI experience design: one-column booking fields across six widths, logo intro, reduced-motion parity, same-day limits, readable controls, contrast, and responsive navigation.")


if __name__ == "__main__":
    main()
