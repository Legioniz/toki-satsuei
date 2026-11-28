#!/usr/bin/env python3
"""Run TOKI SATSUEI local build, security, CSS, and browser QA suites."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAST_CHECKS: list[tuple[str, list[str]]] = [
    ("Sync security policy", [sys.executable, "scripts/sync_security_policy.py", "--check"]),
    ("Check CSS bundles", [sys.executable, "scripts/build-css.py", "--check"]),
    ("Rebuild media library manifest", [sys.executable, "scripts/build-toki-media-library.py"]),
    ("Compile Python scripts and tests", [sys.executable, "-m", "compileall", "-q", "scripts", "tests"]),
    ("CSS bundle QA", [sys.executable, "tests/toki-css-bundle-qa.py"]),
    ("Asset integration QA", [sys.executable, "tests/toki-asset-integration-qa.py"]),
    ("Self-hosted media QA", [sys.executable, "tests/toki-self-hosted-media-qa.py"]),
    ("Static security QA", [sys.executable, "tests/toki-security-static-qa.py"]),
    ("API contract QA", [sys.executable, "tests/toki-api-contract-qa.py"]),
    ("Email notification QA", [sys.executable, "tests/toki-email-notification-qa.py"]),
    ("Fingerprint self-test", [sys.executable, "scripts/fingerprint_assets.py", "--self-test"]),
    ("Pages & Workers static build QA", [sys.executable, "tests/toki-worker-static-build-qa.py"]),
]

JS_FILES = [
    "motion-system.js",
    "site.js",
    "availability.js",
    "library.js",
    "admin.js",
    "client-gallery.js",
    "equipment-viewer.js",
    "worker.mjs",
]

BROWSER_CHECKS: list[tuple[str, list[str]]] = [
    ("Layout browser QA", [sys.executable, "tests/toki-layout-browser-qa.py"]),
    ("Orientation QA", [sys.executable, "tests/toki-orientation-qa.py"]),
    ("Adaptive interaction QA", [sys.executable, "tests/toki-adaptive-interaction-qa.py"]),
    ("Equipment viewer QA", [sys.executable, "tests/toki-equipment-qa.py"]),
    ("Scroll motion QA", [sys.executable, "tests/toki-scroll-motion-qa.py"]),
    ("Experience design QA", [sys.executable, "tests/toki-experience-design-qa.py"]),
    ("Public pages QA", [sys.executable, "tests/toki-public-pages-qa.py"]),
    ("Booking browser QA", [sys.executable, "tests/toki-booking-browser-qa.py"]),
    ("Pricing calculator QA", [sys.executable, "tests/toki-pricing-calculator-qa.py"]),
    ("Admin dashboard QA", [sys.executable, "tests/toki-admin-dashboard-qa.py"]),
    ("Client gallery QA", [sys.executable, "tests/toki-client-gallery-qa.py"]),
    ("Availability calendar QA", [sys.executable, "tests/toki-availability-calendar-qa.py"]),
    ("Cinematic design QA", [sys.executable, "tests/toki-cinematic-design-qa.py"]),
    ("Build static Pages output for mobile QA", [sys.executable, "scripts/build_static_site.py", "--target", "pages"]),
    ("Fingerprint static Pages output", [sys.executable, "scripts/fingerprint_assets.py", "dist"]),
    ("Mobile browser & image QA", [sys.executable, "tests/toki-mobile-browser-image-qa.py"]),
]

LIVE_CHECKS: list[tuple[str, list[str]]] = [
    ("Live Supabase HTTP security QA", [sys.executable, "tests/toki-live-http-security-qa.py"]),
]


def run_step(label: str, cmd: list[str]) -> bool:
    print(f"\n==> {label}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"FAIL: {label} (exit {result.returncode})")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TOKI SATSUEI QA checks.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fast", action="store_true", help="Run fast static, syntax, CSS, and build checks (default).")
    group.add_argument("--browser", action="store_true", help="Run Playwright browser QA checks.")
    group.add_argument("--all", action="store_true", help="Run fast checks and Playwright browser QA checks.")
    parser.add_argument("--live", action="store_true", help="Also run live Supabase HTTP security checks.")
    args = parser.parse_args()

    run_fast = args.fast or args.all or (not args.browser and not args.live)
    run_browser = args.browser or args.all

    steps: list[tuple[str, list[str]]] = []
    if run_fast:
        if shutil.which("node"):
            for js in JS_FILES:
                steps.append((f"JS syntax ({js})", ["node", "--check", js]))
            steps.append(("Worker runtime QA", ["node", "tests/toki-worker-runtime-qa.mjs"]))
        else:
            print("WARN: node not found; skipping JS syntax and Worker runtime QA.")
        steps.extend(FAST_CHECKS)

    if run_browser:
        steps.extend(BROWSER_CHECKS)

    if args.live:
        steps.extend(LIVE_CHECKS)

    failed: list[str] = []
    for label, cmd in steps:
        if not run_step(label, cmd):
            failed.append(label)

    print(f"\nSummary: {len(steps) - len(failed)}/{len(steps)} passed.")
    if failed:
        print("Failed steps:")
        for item in failed:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
