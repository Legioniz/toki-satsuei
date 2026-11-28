#!/usr/bin/env python3
"""Build curated TOKI static-site directories for GitHub Pages, Cloudflare Pages mirror, or Workers.

Only the public page/runtime allowlist and the public media directories are copied.
Repository source, CI workflows, tests, Supabase functions, and owner-only tooling
are never included in either deployment directory.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_ROOT_FILES = (
    "index.html",
    "booking.html",
    "library.html",
    "policies.html",
    "404.html",
    "admin.html",
    "client-gallery.html",
    "robots.txt",
    "sitemap.xml",
)

PUBLIC_JS_FILES = (
    "motion-system.js",
    "site.js",
    "equipment-viewer.js",
    "availability.js",
    "library.js",
    "admin.js",
    "client-gallery.js",
)

PUBLIC_DIRECTORIES = ("assets", "data")
PAGES_ONLY_FILES = ("_headers",)
PAGES_ONLY_MARKERS = (".nojekyll",)

REQUIRED_FILES = (
    "index.html",
    "booking.html",
    "library.html",
    "policies.html",
    "404.html",
    "admin.html",
    "client-gallery.html",
    "assets/css/toki-home.css",
    "assets/css/toki-archive.css",
    "assets/css/toki-policies.css",
    "assets/css/toki-404.css",
    "assets/css/toki-admin.css",
    "assets/css/toki-client.css",
    "assets/js/motion-system.js",
    "assets/js/site.js",
    "assets/js/equipment-viewer.js",
    "assets/js/availability.js",
    "assets/js/library.js",
    "assets/js/admin.js",
    "assets/js/client-gallery.js",
    "data/media-library.json",
    "robots.txt",
    "sitemap.xml",
    "assets/brand/Toki-Satsuei-Brushstroke-Emblem.png",
    "assets/equipment/camera/EOS-3000D-front.png",
    "assets/equipment/camera/EOS-3000D-pop-up-flash.png",
    "assets/equipment/camera/EOS-3000D-left-side.png",
    "assets/equipment/camera/EOS-3000D-right-side.png",
    "assets/equipment/camera/EOS-3000D-top.png",
)


def run_preflight_scripts() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-css.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-toki-media-library.py")],
        cwd=ROOT,
        check=True,
    )


def build_static_site(target: str, output: Path | None = None) -> Path:
    if target not in {"pages", "worker"}:
        raise ValueError(f"Unsupported static-site target: {target}")

    run_preflight_scripts()

    if output is None:
        output = ROOT / ("dist" if target == "pages" else "worker-dist")
    output = output.resolve()
    if output == ROOT or output in ROOT.parents:
        raise ValueError(f"Refusing to replace a repository or parent directory: {output}")

    root_files = list(PUBLIC_ROOT_FILES)
    markers: list[str] = []
    if target == "pages":
        root_files.extend(PAGES_ONLY_FILES)
        markers.extend(PAGES_ONLY_MARKERS)

    for name in root_files:
        source = ROOT / name
        if not source.is_file():
            raise FileNotFoundError(f"Required public site file is missing: {source}")

    for name in PUBLIC_DIRECTORIES:
        source = ROOT / name
        if not source.is_dir():
            raise FileNotFoundError(f"Required public site directory is missing: {source}")

    if output.exists():
        if output.is_dir() and not output.is_symlink():
            shutil.rmtree(output)
        else:
            output.unlink()
    output.mkdir(parents=True, exist_ok=True)

    for name in root_files:
        shutil.copy2(ROOT / name, output / name)
    for name in PUBLIC_DIRECTORIES:
        shutil.copytree(ROOT / name, output / name)

    # Runtime JavaScript is authored in src/js and published under assets/js.
    js_output = output / "assets" / "js"
    js_output.mkdir(parents=True, exist_ok=True)
    for name in PUBLIC_JS_FILES:
        source = ROOT / "src" / "js" / name
        if not source.is_file():
            raise FileNotFoundError(f"Required browser runtime is missing: {source}")
        shutil.copy2(source, js_output / name)

    for marker in markers:
        (output / marker).touch()

    expected_entries = set(root_files) | set(PUBLIC_DIRECTORIES) | set(markers)
    actual_entries = {path.name for path in output.iterdir()}
    if actual_entries != expected_entries:
        unexpected = sorted(actual_entries - expected_entries)
        missing = sorted(expected_entries - actual_entries)
        raise AssertionError(
            f"Static output allowlist mismatch for {target}: "
            f"unexpected={unexpected}, missing={missing}"
        )

    missing_files = [name for name in REQUIRED_FILES if not (output / name).is_file()]
    if missing_files:
        raise AssertionError(
            f"Static output is missing required files for {target}: {missing_files}"
        )

    file_count = sum(path.is_file() for path in output.rglob("*"))
    print(
        f"PASS {target} static output: {file_count} files in {output}; "
        f"top-level allowlist contains {len(expected_entries)} entries."
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("pages", "worker"), default="pages")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build_static_site(args.target, args.output)


if __name__ == "__main__":
    main()
