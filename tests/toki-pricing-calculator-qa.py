#!/usr/bin/env python3
"""QA test suite for TOKI SATSUEI interactive pricing calculator."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

RATES = {
    "Quick Snap": {"base": 200, "included": 1, "duration": 15},
    "Toki Portraits": {"base": 350, "included": 1, "duration": 30},
    "Signature Session": {"base": 500, "included": 1, "duration": 60},
    "Duo Session": {"base": 450, "included": 2, "duration": 30},
}


def calculate_price(package: str, participants: int, extra_photos: int, extra_time_steps: int) -> tuple[int, int, int, int]:
    data = RATES[package]
    base = data["base"]
    extra_parts = max(0, participants - data["included"])
    part_cost = extra_parts * 50
    photo_cost = extra_photos * 30
    time_cost = extra_time_steps * 75
    addons = part_cost + photo_cost + time_cost
    total = base + addons
    deposit = round(total * 0.20)
    return base, addons, total, deposit


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def main() -> None:
    # 1. Pure logic verification across all rate matrix combinations
    assert calculate_price("Quick Snap", 1, 0, 0) == (200, 0, 200, 40)
    assert calculate_price("Toki Portraits", 1, 0, 0) == (350, 0, 350, 70)
    assert calculate_price("Signature Session", 1, 0, 0) == (500, 0, 500, 100)
    assert calculate_price("Duo Session", 2, 0, 0) == (450, 0, 450, 90)

    # Solo with 2 participants (1 extra): 350 + 50 = 400
    assert calculate_price("Toki Portraits", 2, 0, 0) == (350, 50, 400, 80)
    # Duo with 2 participants (0 extra): 450 + 0 = 450
    assert calculate_price("Duo Session", 2, 0, 0) == (450, 0, 450, 90)
    # Duo with 3 participants (1 extra): 450 + 50 = 500
    assert calculate_price("Duo Session", 3, 0, 0) == (450, 50, 500, 100)
    # Duo with 3 participants + 2 photos + 1 extra 15m: 450 + 50 + 60 + 75 = 635
    assert calculate_price("Duo Session", 3, 2, 1) == (450, 185, 635, 127)

    # 2. Browser interaction verification
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            context.route("https://challenges.cloudflare.com/**", lambda route: route.abort())
            page = context.new_page()
            page.goto(base_url + "/index.html#sessions", wait_until="domcontentloaded")

            calc = page.locator("#pricing-calculator")
            assert calc.is_visible()

            # Page-owned styles must win through normal cascade order and scoped selectors.
            def computed(selector: str, property_name: str) -> str:
                values = page.locator(selector).evaluate_all(
                    "(nodes, property) => nodes.map(node => getComputedStyle(node).getPropertyValue(property).trim())",
                    property_name,
                )
                assert values, f"No elements found for computed-style check: {selector}"
                assert all(value == values[0] for value in values), (
                    f"Inconsistent computed values for {selector} {property_name}: {values}"
                )
                return values[0]

            expected_styles = (
                (".calculator-wrap .section-heading h2", "color", "rgb(245, 242, 235)"),
                (".calculator-wrap .section-heading h2 em", "color", "rgb(216, 117, 125)"),
                (".calculator-wrap .section-aside", "color", "rgb(212, 204, 193)"),
                (".calc-label", "color", "rgb(245, 242, 235)"),
                (".calc-select", "color", "rgb(255, 255, 255)"),
                (".calc-select", "background-color", "rgb(20, 19, 20)"),
                (".calc-btn-step", "color", "rgb(255, 255, 255)"),
                (".calc-input-qty", "color", "rgb(255, 255, 255)"),
                (".calc-summary-card h3", "color", "rgb(255, 255, 255)"),
                (".calc-breakdown-list li", "color", "rgb(229, 222, 212)"),
                (".calc-total-label", "color", "rgb(255, 255, 255)"),
                (".calc-total-val", "color", "rgb(245, 242, 235)"),
                (".calc-disclaimer", "color", "rgb(209, 200, 190)"),
                (".calc-apply-btn", "background-color", "rgb(163, 31, 45)"),
                (".calc-apply-btn", "color", "rgb(255, 255, 255)"),
            )
            for selector, property_name, expected in expected_styles:
                actual = computed(selector, property_name)
                assert actual == expected, (
                    f"Pricing calculator cascade mismatch for {selector} {property_name}: "
                    f"expected {expected}, got {actual}"
                )

            apply_button = page.locator("#calc-apply-to-booking")
            apply_button.hover()
            # Wait until the full hover transition has settled before asserting
            # the final color, outline, and lift. :hover alone is only the first frame.
            try:
                page.wait_for_function(
                    """() => {
                        const button = document.querySelector("#calc-apply-to-booking");
                        if (!button || !button.matches(":hover")) return false;
                        const style = getComputedStyle(button);
                        return style.backgroundColor === "rgb(184, 40, 55)" &&
                            style.borderTopColor === "rgb(163, 31, 45)";
                    }""",
                    timeout=4000,
                )
            except Exception as error:
                hover_state = apply_button.evaluate("""button => {
                    const style = getComputedStyle(button);
                    const rect = button.getBoundingClientRect();
                    const hit = document.elementFromPoint(
                        rect.left + rect.width / 2,
                        rect.top + rect.height / 2
                    );
                    return {
                        isHovered: button.matches(":hover"),
                        pageRuleMatches: button.matches(".calculator-wrap .calc-apply-btn:hover"),
                        pageRoot: button.closest("#pricing-calculator")?.className ?? null,
                        backgroundColor: style.backgroundColor,
                        borderTopColor: style.borderTopColor,
                        surfaceToken: style.getPropertyValue("--toki-button-surface").trim(),
                        transform: style.transform,
                        transitionProperty: style.transitionProperty,
                        transitionDuration: style.transitionDuration,
                        hitTarget: hit?.outerHTML?.slice(0, 220) ?? null
                    };
                }""")
                raise AssertionError(
                    f"Calculator hover cascade did not settle: {hover_state}"
                ) from error
            hover_style = apply_button.evaluate("""button => {
                const style = getComputedStyle(button);
                return {
                    backgroundColor: style.backgroundColor,
                    borderTopColor: style.borderTopColor,
                    surfaceToken: style.getPropertyValue("--toki-button-surface").trim(),
                    transform: style.transform
                };
            }""")
            assert hover_style["surfaceToken"] == "#b82837", (
                f"Calculator hover token must resolve from the page-scoped state: {hover_style}"
            )

            # Verify initial default state (Toki Portraits)
            assert "₱350" in page.locator("#calc-total-display").inner_text()
            assert "₱70" in page.locator("#calc-breakdown-list").inner_text()
            assert page.locator("#calc-part-minus").is_disabled(), "Participant decrement should be disabled at its minimum"
            assert page.locator("#calc-photo-minus").is_disabled(), "Photo decrement should be disabled at zero"
            assert page.locator("#calc-time-minus").is_disabled(), "Time decrement should be disabled at zero"

            # Select Duo Session
            page.locator("#calc-package-select").select_option("Duo Session")
            assert "₱450" in page.locator("#calc-total-display").inner_text()
            assert "₱90" in page.locator("#calc-breakdown-list").inner_text()
            assert page.locator("#calc-part-qty").input_value() == "2"

            # Add participant (+1 -> 3)
            page.locator("#calc-part-plus").click()
            assert page.locator("#calc-part-qty").input_value() == "3"
            assert "₱500" in page.locator("#calc-total-display").inner_text()

            # Add 2 photos (+2 -> 2)
            page.locator("#calc-photo-plus").click()
            page.locator("#calc-photo-plus").click()
            assert page.locator("#calc-photo-qty").input_value() == "2"
            assert "₱560" in page.locator("#calc-total-display").inner_text()

            # Add 1 time step (+1 -> 15 min)
            page.locator("#calc-time-plus").click()
            assert page.locator("#calc-time-qty").input_value() == "15"
            assert "₱635" in page.locator("#calc-total-display").inner_text()
            assert "₱127" in page.locator("#calc-breakdown-list").inner_text()

            # Every stepper enforces and exposes its exact lower and upper limits.
            assert page.locator("#calc-part-minus").is_enabled(), "Participant decrement should work above two"
            for _ in range(9):
                page.locator("#calc-part-plus").click()
            assert page.locator("#calc-part-qty").input_value() == "12"
            assert page.locator("#calc-part-plus").is_disabled(), "Participant increment remained active above twelve"
            for _ in range(10):
                page.locator("#calc-part-minus").click()
            assert page.locator("#calc-part-qty").input_value() == "2"
            assert page.locator("#calc-part-minus").is_disabled(), "Duo Session allows decrement below two participants"
            page.locator("#calc-part-plus").click()
            assert page.locator("#calc-part-qty").input_value() == "3"

            for _ in range(48):
                page.locator("#calc-photo-plus").click()
            assert page.locator("#calc-photo-qty").input_value() == "50"
            assert page.locator("#calc-photo-plus").is_disabled(), "Photo increment remained active above fifty"
            for _ in range(48):
                page.locator("#calc-photo-minus").click()
            assert page.locator("#calc-photo-qty").input_value() == "2"

            for _ in range(7):
                page.locator("#calc-time-plus").click()
            assert page.locator("#calc-time-qty").input_value() == "120"
            assert page.locator("#calc-time-plus").is_disabled(), "Time increment remained active above 120 minutes"
            for _ in range(7):
                page.locator("#calc-time-minus").click()
            assert page.locator("#calc-time-qty").input_value() == "15"
            assert page.locator("#calc-total-display").inner_text() == "₱635", "Stepper boundary checks changed the quotation"

            # Click Apply to Booking Form
            page.locator("#calc-apply-to-booking").click()
            page.wait_for_function("location.pathname.endsWith('/booking.html')")

            # Verify values prefilled on the separate booking page
            form_session = page.locator('select[name="session"]').input_value()
            form_participants = page.locator('input[name="participants"]').input_value()
            form_notes = page.locator('textarea[name="notes"]').input_value()

            assert form_session == "Duo Session"
            assert form_participants == "3"
            assert page.locator('input[name="additional_photos"]').input_value() == "2"
            assert page.locator('input[name="additional_time"]').input_value() == "15"
            assert "Requested add-ons: 2 extra edited photos, 15 min extra time." in form_notes

            browser.close()
    finally:
        server.shutdown()

    print("PASS TOKI pricing calculator QA: exact package rates, participant inclusions, add-on mathematics, deposit estimation, and booking form synchronization.")


if __name__ == "__main__":
    main()
