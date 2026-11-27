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
