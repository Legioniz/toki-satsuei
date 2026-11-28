#!/usr/bin/env python3
"""Prove Pages and Workers packages contain only their intended public assets."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_static_site import (  # noqa: E402
    PUBLIC_DIRECTORIES,
    PUBLIC_ROOT_FILES,
    PAGES_ONLY_FILES,
    PAGES_ONLY_MARKERS,
    build_static_site,
)


def run_fingerprint(directory: Path) -> None:
    script = ROOT / "scripts" / "fingerprint_assets.py"
    subprocess.run([sys.executable, str(script), str(directory)], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(script), str(directory), "--verify-only"],
        cwd=ROOT,
        check=True,
    )


def verify_target(directory: Path, target: str) -> None:
    expected = set(PUBLIC_ROOT_FILES) | set(PUBLIC_DIRECTORIES)
    if target == "pages":
        expected.update(PAGES_ONLY_FILES)
        expected.update(PAGES_ONLY_MARKERS)
    actual = {path.name for path in directory.iterdir()}
    assert actual == expected, (
        f"{target} package root is not allowlisted: "
        f"unexpected={sorted(actual - expected)}, missing={sorted(expected - actual)}"
    )

    forbidden = {".github", "tests", "scripts", "supabase", "README.md", "SECURITY.md"}
    leaked = sorted(forbidden & actual)
    assert not leaked, f"{target} package contains repository-only content: {leaked}"

    for required in (
        "index.html",
        "booking.html",
        "library.html",
        "policies.html",
        "404.html",
        "admin.html",
        "client-gallery.html",
        "data/media-library.json",
        "assets/css/toki-home.css",
        "assets/css/toki-archive.css",
        "assets/css/toki-policies.css",
        "assets/css/toki-404.css",
        "assets/css/toki-admin.css",
        "assets/css/toki-client.css",
        "assets/js/motion-system.js",
        "assets/js/site.js",
        "assets/js/availability.js",
        "assets/js/library.js",
        "assets/js/admin.js",
        "assets/js/client-gallery.js",
        "assets/js/equipment-viewer.js",
    ):
        assert (directory / required).is_file(), f"{target} package is missing {required}"


def main() -> None:
    config_path = ROOT / "wrangler.worker.jsonc"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config.get("name") == "toki-satsuei", "Worker config targets the wrong Worker"
    assert config.get("assets", {}).get("directory") == "./worker-dist", (
        "Worker must deploy the curated worker-dist directory, never the repository root"
    )
    assert config.get("main") == "./src/worker/worker.mjs", "Worker must use the security-header wrapper"
    assets_config = config.get("assets", {})
    assert assets_config.get("binding") == "ASSETS", "Worker asset binding must be ASSETS"
    assert assets_config.get("run_worker_first") is True, "Worker wrapper must run for static asset requests"
    assert (ROOT / "src" / "worker" / "worker.mjs").is_file(), "Worker runtime wrapper is missing"

    with tempfile.TemporaryDirectory(prefix="toki-static-output-") as temporary:
        root = Path(temporary)
        pages = build_static_site("pages", root / "pages")
        worker = build_static_site("worker", root / "worker")

        verify_target(pages, "pages")
        verify_target(worker, "worker")

        assert (pages / "_headers").is_file(), "Pages package must retain Cloudflare Pages headers"
        assert not (worker / "_headers").exists(), "Worker package must not include Pages-only _headers"
        assert (pages / ".nojekyll").is_file(), "Pages package must retain .nojekyll"
        assert not (worker / ".nojekyll").exists(), "Worker package must omit Pages-only .nojekyll"

        run_fingerprint(pages)
        run_fingerprint(worker)

    print(
        "PASS TOKI static build QA: Pages and Workers outputs use explicit allowlists; "
        "repository-only files are excluded; both packages have valid SHA-256 fingerprints."
    )


if __name__ == "__main__":
    main()
