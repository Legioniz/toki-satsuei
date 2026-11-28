"""Verify page bundles and the modular TOKI stylesheet source architecture."""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "index.html": "toki-home.css",
    "booking.html": "toki-home.css",
    "library.html": "toki-archive.css",
    "policies.html": "toki-policies.css",
    "404.html": "toki-404.css",
    "admin.html": "toki-admin.css",
    "client-gallery.html": "toki-client.css",
}
REQUIRED_MODULES = (
    "styles/tokens.css",
    "styles/base.css",
    "styles/components.css",
    "styles/shared/foundation.css",
    "styles/shared/refinements.css",
    "styles/shared/cinematic.css",
    "styles/shared/motion-system.css",
    "styles/pages/home-booking.css",
    "styles/shared/compatibility-fixes.css",
    "styles/shared/orientation.css",
    "styles/shared/global-motion.css",
    "styles/shared/site-enhancements.css",
    "styles/shared/motion-refinements.css",
    "styles/shared/mobile-navigation.css",
    "styles/pages/policies.css",
    "styles/pages/availability.css",
    "styles/pages/pricing-calculator.css",
    "styles/pages/equipment.css",
    "styles/pages/archive.css",
    "styles/pages/admin.css",
    "styles/pages/gallery.css",
    "styles/pages/page-shells.css",
)
def duplicate_css_rules(css):
    """Return exact duplicate CSS rules within the same at-rule context."""
    grouping_at_rules = {
        "@media", "@supports", "@container", "@layer", "@document",
        "@scope", "@keyframes", "@-webkit-keyframes",
    }
    stack = []
    prelude = []
    duplicates = {}
    quote = None
    escaped = False
    comment = False
    skip_comment_closing_slash = False

    def active_body():
        for node in reversed(stack):
            if node["kind"] in ("rule", "opaque"):
                return node["body"]
        return None

    for index, char in enumerate(css):
        next_char = css[index + 1] if index + 1 < len(css) else ""
        if skip_comment_closing_slash:
            skip_comment_closing_slash = False
            continue
        if comment:
            if char == "*" and next_char == "/":
                comment = False
                skip_comment_closing_slash = True
            continue
        if quote:
            body = active_body()
            target = body if body is not None else prelude
            target.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "/" and next_char == "*":
            comment = True
            continue
        if char in ("'", '"'):
            quote = char
            target = active_body()
            (target if target is not None else prelude).append(char)
            continue
        if char == "{":
            selector = "".join(prelude).strip()
            prelude.clear()
            if selector.startswith("@"):
                match = re.match(r"@[-\w]+", selector)
                keyword = match.group(0).lower() if match else selector.lower()
                kind = "group" if keyword in grouping_at_rules else "opaque"
                stack.append({"kind": kind, "selector": re.sub(r"\s+", " ", selector), "body": []})
            elif any(node["kind"] == "opaque" for node in stack):
                stack.append({"kind": "opaque-nested", "body": []})
            else:
                context = tuple(node["selector"] for node in stack if node["kind"] == "group")
                stack.append({
                    "kind": "rule",
                    "selector": re.sub(r"\s+", " ", selector),
                    "context": context,
                    "body": [],
                })
        elif char == "}":
            if stack:
                node = stack.pop()
                if node["kind"] == "rule":
                    body = re.sub(r"\s+", " ", "".join(node["body"])).strip()
                    signature = (node["context"], node["selector"], body)
                    duplicates[signature] = duplicates.get(signature, 0) + 1
        elif char == ";" and active_body() is None:
            prelude.clear()
        else:
            target = active_body()
            (target if target is not None else prelude).append(char)

    return {
        signature: count
        for signature, count in duplicates.items()
        if count > 1
    }

def main():
    for page, bundle in EXPECTED.items():
        links = re.findall(r'<link rel="stylesheet" href="\./([a-z0-9-]+\.css)">',
                           (ROOT / page).read_text(encoding="utf-8"))
        assert links == [bundle], f"{page} should link only {bundle}, found {links}"
        source = (ROOT / page).read_text(encoding="utf-8")
        assert not re.search(r'(?:href|src)="\./[^"]+\?v=', source), (
            f"{page} must not hard-code cache fingerprints; the build generates them."
        )

    missing = [path for path in REQUIRED_MODULES if not (ROOT / path).is_file()]
    assert not missing, "Missing modular stylesheet source(s): " + ", ".join(missing)

    for module in REQUIRED_MODULES:
        duplicates = duplicate_css_rules((ROOT / module).read_text(encoding="utf-8"))
        assert not duplicates, (
            f"{module} contains exact duplicate CSS rule blocks: "
            + "; ".join(f"{selector} ({count} copies)" for (_, selector, _), count in duplicates.items())
        )

    mobile_navigation = (ROOT / "styles/shared/mobile-navigation.css").read_text(encoding="utf-8")
    assert mobile_navigation.count("@media (max-width: 820px)") == 1
    assert mobile_navigation.count(".site-header .primary-nav {") == 1
    sticky_guard = re.search(
        r"body:has\(\.site-header \.primary-nav\.is-open\) \.mobile-cta,\s*"
        r"body:has\(\.site-header \.primary-nav\.is-open\) \.back-to-top\s*\{([^{}]*)\}",
        mobile_navigation, flags=re.S,
    )
    assert sticky_guard and sticky_guard.group(1).count("!important") == 4
    assert "!important" not in mobile_navigation.replace(sticky_guard.group(0), "")
    assert not (ROOT / "design-system.css").exists(), "The monolithic design-system.css must stay retired."
    for retired in (
        "design-system.css", "policies.css", "availability.css", "pricing-calculator.css",
        "equipment.css", "library.css", "admin.css", "client-gallery.css", "pages.css",
        "styles.css", "refinement.css", "cinematic.css", "motion-system.css", "experience.css",
        "fixes.css", "global-motion.css", "mobile-nav.css", "motion-refinements.css",
        "orientation.css", "site-enhancements.css",
    ):
        assert not (ROOT / retired).exists(), f"Page stylesheet remains at the repository root: {retired}"

    tokens = (ROOT / "styles" / "tokens.css").read_text(encoding="utf-8")
    for name, query in (
        ("--toki-compact", "(max-width: 520px)"),
        ("--toki-mobile", "(max-width: 680px)"),
        ("--toki-tablet", "(max-width: 960px)"),
        ("--toki-wide", "(min-width: 1200px)"),
    ):
        assert f"@custom-media {name} {query};" in tokens, f"Missing breakpoint token {name}"

    builder = (ROOT / "scripts" / "build-css.py").read_text(encoding="utf-8")
    assert "CUSTOM_MEDIA" in builder and "@media" in builder, "The builder must expand custom media tokens before deployment"

    pricing_css = (ROOT / "styles/pages/pricing-calculator.css").read_text(encoding="utf-8")
    components_css = (ROOT / "styles/components.css").read_text(encoding="utf-8")
    home_booking_css = (ROOT / "styles/pages/home-booking.css").read_text(encoding="utf-8")
    assert "!important" not in pricing_css
    assert ".calculator-wrap .section-heading .section-aside" in pricing_css
    assert ".calculator-wrap .section-aside" not in components_css
    assert ".sessions-section .section-aside" not in components_css
    assert ".sessions-section > .section-heading .section-aside" in components_css
    assert ".sessions-section .section-aside" not in home_booking_css
    assert ".sessions-section > .section-heading .section-aside" in home_booking_css
    home_bundle_match = re.search(r'"toki-home\.css": \[([\s\S]*?)\],\s*"toki-archive\.css"', builder)
    assert home_bundle_match
    home_bundle = home_bundle_match.group(1)
    assert home_bundle.index('"design-system"') < home_bundle.index('"pricing-calculator"')
    for module in REQUIRED_MODULES:
        assert f'"{module}"' in builder, f"{module} is not mapped into the generated bundle manifest."

    for bundle in EXPECTED.values():
        output = (ROOT / bundle).read_text(encoding="utf-8")
        assert "@custom-media" not in output, f"{bundle} leaks source-only custom media definitions"
        assert "@media (--toki-" not in output, f"{bundle} leaks unresolved breakpoint tokens"

    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-css.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    print("PASS TOKI CSS architecture QA: page bundles, tokens/base/components, page modules, and generated outputs are current")

if __name__ == "__main__":
    main()
