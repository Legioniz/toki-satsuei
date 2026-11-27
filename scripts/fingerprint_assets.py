#!/usr/bin/env python3
"""Fingerprint local static assets with SHA-256 and verify every local reference."""
from __future__ import annotations

import argparse
import hashlib
import re
import tempfile
from pathlib import Path

HASH_LENGTH = 32
ASSET_SUFFIXES = {
    ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".webp", ".avif",
    ".svg", ".gif", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".otf", ".ico",
}
TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".svg"}

CSP_META = (
    "default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; "
    "script-src 'self' https://static.sketchfab.com https://challenges.cloudflare.com "
    "https://*.challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https://pjuwrngnrrvdiwqspkic.supabase.co "
    "https://challenges.cloudflare.com https://*.challenges.cloudflare.com "
    "https://*.cloudflareinsights.com; "
    "frame-src 'self' https://sketchfab.com https://*.sketchfab.com "
    "https://challenges.cloudflare.com https://*.challenges.cloudflare.com; "
    "upgrade-insecure-requests"
)


def digest(path: Path) -> str:
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    return value[:HASH_LENGTH]


def pattern_for(relative_path: str) -> re.Pattern[str]:
    # Require a local path boundary. The negative lookbehind prevents matching the
    # path segment inside an absolute third-party URL such as https://host/assets/x.
    return re.compile(
        r"(?<![A-Za-z0-9:/])(?P<prefix>\.\.?/|/)?"
        + re.escape(relative_path)
        + r"(?P<query>\?[^\"'\s<>)#]*)?(?P<fragment>#[^\"'\s<>)]+)?"
    )


def update_references(text: str, relative_path: str, fingerprint: str) -> tuple[str, int]:
    pattern = pattern_for(relative_path)

    def replace(match: re.Match[str]) -> str:
        old_query = (match.group("query") or "").lstrip("?")
        params = [part for part in old_query.split("&") if part and not part.startswith("v=")]
        params.append("v=" + fingerprint)
        return (
            (match.group("prefix") or "")
            + relative_path
            + "?"
            + "&".join(params)
            + (match.group("fragment") or "")
        )

    return pattern.subn(replace, text)


def documents(root: Path) -> list[Path]:
    return sorted(
        item for item in root.rglob("*")
        if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES
    )


def rewrite_stage(root: Path, sources: list[Path]) -> int:
    total = 0
    text_paths = documents(root)
    for source in sources:
        relative = source.relative_to(root).as_posix()
        fingerprint = digest(source)
        for target in text_paths:
            if target == source:
                continue
            try:
                old = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            new, count = update_references(old, relative, fingerprint)
            if count:
                target.write_text(new, encoding="utf-8", newline="\n")
                total += count
    return total


def verify_references(root: Path) -> list[str]:
    root = root.resolve()
    assets = sorted(
        item for item in root.rglob("*")
        if item.is_file() and item.suffix.lower() in ASSET_SUFFIXES
    )
    files = documents(root)
    errors: list[str] = []
    for source in assets:
        relative = source.relative_to(root).as_posix()
        fingerprint = digest(source)
        pattern = pattern_for(relative)
        for target in files:
            if target == source:
                continue
            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in pattern.finditer(content):
                query = (match.group("query") or "").lstrip("?").split("&")
                versions = [item[2:] for item in query if item.startswith("v=")]
                if versions != [fingerprint]:
                    errors.append(
                        f"{target.relative_to(root).as_posix()} references {relative} "
                        "without its current SHA-256 fingerprint"
                    )
    return errors


def normalize_csp_fallbacks(root: Path) -> int:
    """Put one consistent CSP meta fallback near the start of every HTML head."""
    replacement = f'<meta http-equiv="Content-Security-Policy" content="{CSP_META}">'
    pattern = re.compile(
        r"""<meta\s+http-equiv=["']Content-Security-Policy["'][^>]*>""",
        re.IGNORECASE,
    )
    changed = 0
    for page in sorted(root.rglob("*.html")):
        old = page.read_text(encoding="utf-8")
        new, count = pattern.subn(replacement, old)
        if count == 0:
            charset = re.search(
                r"""<meta\s+charset=["'][^"']+["'][^>]*>""",
                new,
                re.IGNORECASE,
            )
            if charset:
                insertion_point = charset.end()
            else:
                head = re.search(r"<head(?:\s[^>]*)?>", new, re.IGNORECASE)
                if not head:
                    raise AssertionError(f"HTML document is missing a head element: {page}")
                insertion_point = head.end()
            new = new[:insertion_point] + "\n  " + replacement + new[insertion_point:]
            count = 1
        if new != old:
            page.write_text(new, encoding="utf-8", newline="\n")
            changed += count
    return changed


def fingerprint_assets(root: Path) -> tuple[int, int]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Asset directory does not exist: {root}")

    normalize_csp_fallbacks(root)
    assets = sorted(
        item for item in root.rglob("*")
        if item.is_file() and item.suffix.lower() in ASSET_SUFFIXES
    )
    binary = [
        item for item in assets
        if item.suffix.lower() not in {".css", ".js", ".json", ".svg"}
    ]
    svg = [item for item in assets if item.suffix.lower() == ".svg"]
    manifests = [item for item in assets if item.suffix.lower() == ".json"]
    code = [item for item in assets if item.suffix.lower() in {".css", ".js"}]

    # Update leaf resources first; then manifests and code that point to them.
    updated = rewrite_stage(root, binary)
    updated += rewrite_stage(root, svg)
    updated += rewrite_stage(root, manifests)
    updated += rewrite_stage(root, code)

    errors = verify_references(root)
    if errors:
        raise AssertionError("Asset fingerprint verification failed:\n- " + "\n- ".join(errors))
    return len(assets), updated


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="toki-fingerprint-") as temporary:
        root = Path(temporary)
        (root / "assets").mkdir()
        image = root / "assets" / "sample.webp"
        image.write_bytes(b"initial image payload")
        (root / "manifest.json").write_text(
            '{"items":[{"src":"./assets/sample.webp?v=manual"}]}', encoding="utf-8"
        )
        (root / "library.js").write_text(
            'fetch("./manifest.json?v=manual");', encoding="utf-8"
        )
        (root / "site.css").write_text(
            '.sample{background-image:url("./assets/sample.webp?v=manual")}', encoding="utf-8"
        )
        (root / "index.html").write_text(
            '<link rel="stylesheet" href="./site.css?v=manual">'
            '<script src="./library.js?v=manual"></script>'
            '<img src="./assets/sample.webp?v=manual">'
            '<script src="https://cdn.example/assets/sample.webp"></script>',
            encoding="utf-8",
        )

        count, updated = fingerprint_assets(root)
        assert count == 4, f"Expected four fingerprinted files, got {count}"
        assert updated >= 5, f"Expected nested references to update, got {updated}"
        assert not verify_references(root)

        before = {item.relative_to(root): item.read_bytes() for item in root.rglob("*") if item.is_file()}
        fingerprint_assets(root)
        after = {item.relative_to(root): item.read_bytes() for item in root.rglob("*") if item.is_file()}
        assert before == after, "Fingerprint generation must be deterministic and idempotent"

        old = digest(image)
        image.write_bytes(b"updated image payload")
        fingerprint_assets(root)
        assert digest(image) != old, "Changed content must produce a different fingerprint"
        assert not verify_references(root)

        html = (root / "index.html").read_text(encoding="utf-8")
        assert "https://cdn.example/assets/sample.webp" in html, "External URLs must remain untouched"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("PASS cache fingerprint QA: SHA-256 invalidation, nested references, external URL safety, and idempotence.")
        return

    if args.verify_only:
        errors = verify_references(args.directory)
        if errors:
            raise SystemExit("FAIL fingerprint verification:\n- " + "\n- ".join(errors))
        print("PASS packaged asset fingerprint verification.")
        return

    count, updated = fingerprint_assets(args.directory)
    print(
        f"PASS cache fingerprints: {count} local assets; "
        f"{updated} references updated and verified (SHA-256/{HASH_LENGTH * 4}-bit)."
    )


if __name__ == "__main__":
    main()
