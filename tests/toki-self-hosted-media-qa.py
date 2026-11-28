#!/usr/bin/env python3
"""Verify TOKI's same-origin photography and web-font delivery contract."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = (
    "index.html",
    "library.html",
    "booking.html",
    "policies.html",
    "404.html",
    "admin.html",
    "client-gallery.html",
)
REMOTE_ASSET_HOSTS = (
    "media.base44.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)
EXPECTED_PHOTOGRAPHS = {
    "behind-the-camera": (1536, 1159),
    "between-turns": (1536, 1024),
    "colour-in-the-quiet": (1536, 1024),
    "before-the-next-shot": (1536, 1024),
}
EXPECTED_FONT_FAMILIES = {
    "Caveat",
    "Cormorant Garamond",
    "DM Sans",
    "Space Mono",
}
EXPECTED_FONT_FACES = 6
EXPECTED_FONT_LICENSES = 4


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def local_file(public_path: str) -> Path:
    normalized = public_path.removeprefix("./").lstrip("/")
    if not normalized.startswith("assets/"):
        raise AssertionError(f"Expected a same-origin /assets path, got {public_path!r}")
    target = (ROOT / normalized).resolve()
    if ROOT.resolve() not in target.parents:
        raise AssertionError(f"Asset path escapes repository root: {public_path}")
    return target


def attr(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', tag, re.IGNORECASE)
    return match.group(1) if match else None


def verify_photography() -> None:
    manifest_path = ROOT / "assets/photography/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("photographs", [])
    if len(records) != len(EXPECTED_PHOTOGRAPHS):
        raise AssertionError("Photography manifest must contain exactly four approved public photographs")

    seen: set[str] = set()
    for record in records:
        slug = record.get("slug")
        if slug not in EXPECTED_PHOTOGRAPHS or slug in seen:
            raise AssertionError(f"Unexpected or duplicate photograph manifest entry: {slug!r}")
        seen.add(slug)
        expected_width, expected_height = EXPECTED_PHOTOGRAPHS[slug]
        if (record.get("width"), record.get("height")) != (expected_width, expected_height):
            raise AssertionError(f"Incorrect source dimensions for {slug}")
        if abs(float(record.get("aspect_ratio", 0)) - expected_width / expected_height) > 0.00001:
            raise AssertionError(f"Incorrect source aspect ratio for {slug}")
        if not record.get("alt", "").strip():
            raise AssertionError(f"Missing descriptive alt text for {slug}")

        original = local_file(record["original"])
        payload = original.read_bytes()
        if sha256(payload) != record.get("original_sha256"):
            raise AssertionError(f"Original JPEG master checksum changed: {slug}")
        if len(payload) != record.get("original_bytes"):
            raise AssertionError(f"Original JPEG master byte count changed: {slug}")
        with Image.open(original) as source:
            source.verify()
        with Image.open(original) as source:
            oriented = ImageOps.exif_transpose(source)
            if oriented.size != (expected_width, expected_height):
                raise AssertionError(f"Original JPEG dimensions changed: {slug}")
            if source.format != "JPEG":
                raise AssertionError(f"Original master is not JPEG: {slug}")

        for image_format, expected_extension, expected_pil_format in (
            ("jpeg", ".jpg", "JPEG"),
            ("webp", ".webp", "WEBP"),
        ):
            variants = record.get("variants", {}).get(image_format, [])
            if [item.get("width") for item in variants] != [480, 960, 1536]:
                raise AssertionError(f"{slug} {image_format} variants must be 480, 960, and 1536 pixels wide")
            for variant in variants:
                target = local_file(variant["path"])
                variant_payload = target.read_bytes()
                if target.suffix != expected_extension:
                    raise AssertionError(f"Unexpected image variant suffix: {target}")
                if sha256(variant_payload) != variant.get("sha256"):
                    raise AssertionError(f"Image variant checksum mismatch: {target}")
                if len(variant_payload) != variant.get("bytes"):
                    raise AssertionError(f"Image variant byte count mismatch: {target}")
                expected_height_variant = round(expected_height * variant["width"] / expected_width)
                if variant.get("height") != expected_height_variant:
                    raise AssertionError(f"Incorrect variant dimensions in manifest: {target}")
                with Image.open(target) as image:
                    if image.format != expected_pil_format:
                        raise AssertionError(f"Incorrect image encoding: {target}")
                    if image.size != (variant["width"], expected_height_variant):
                        raise AssertionError(f"Incorrect actual image dimensions: {target}")

    if seen != set(EXPECTED_PHOTOGRAPHS):
        raise AssertionError("Photography manifest is missing an approved photograph")


def verify_fonts() -> None:
    root = ROOT / "assets/fonts"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    fonts = manifest.get("fonts", [])
    if len(fonts) != EXPECTED_FONT_FACES:
        raise AssertionError(f"Expected {EXPECTED_FONT_FACES} local font faces, found {len(fonts)}")
    if {item.get("family") for item in fonts} != EXPECTED_FONT_FAMILIES:
        raise AssertionError("Font manifest family set differs from the site's four typefaces")
    expected_weights = {
        ("Caveat", "normal", "400 700"),
        ("Cormorant Garamond", "normal", "400 700"),
        ("Cormorant Garamond", "italic", "400 600"),
        ("DM Sans", "normal", "400 700"),
        ("Space Mono", "normal", "400"),
        ("Space Mono", "normal", "700"),
    }
    actual_weights = {
        (item.get("family"), item.get("style"), str(item.get("weight")))
        for item in fonts
    }
    if actual_weights != expected_weights:
        raise AssertionError("Font manifest does not describe the expected variable ranges and static weights")

    for item in fonts:
        target = local_file(item["path"])
        payload = target.read_bytes()
        if not payload.startswith(b"wOF2"):
            raise AssertionError(f"Font is not a WOFF2 file: {target}")
        if sha256(payload) != item.get("sha256") or len(payload) != item.get("bytes"):
            raise AssertionError(f"Font manifest checksum or byte count mismatch: {target}")

    license_files = sorted((root / "licenses").glob("*-OFL.txt"))
    if len(license_files) != EXPECTED_FONT_LICENSES:
        raise AssertionError(f"Expected {EXPECTED_FONT_LICENSES} font license files")
    for license_file in license_files:
        if b"SIL OPEN FONT LICENSE" not in license_file.read_bytes().upper():
            raise AssertionError(f"Font license is not SIL OFL: {license_file}")

    css = (root / "fonts.css").read_text(encoding="utf-8")
    if "fonts.gstatic.com" in css or "https://" in css:
        raise AssertionError("Self-hosted font CSS contains an external font URL")
    if css.count("@font-face") != EXPECTED_FONT_FACES or "font-display: swap" not in css:
        raise AssertionError("Font CSS is missing expected local faces or font-display: swap")
    for item in fonts:
        filename = Path(item["path"]).name
        if f'url("/assets/fonts/{filename}")' not in css:
            raise AssertionError(f"Font CSS does not declare local face: {filename}")


def verify_pages_and_loading() -> None:
    pages: dict[str, str] = {}
    for page in PUBLIC_PAGES:
        content = (ROOT / page).read_text(encoding="utf-8")
        pages[page] = content
        for host in REMOTE_ASSET_HOSTS:
            if host in content:
                raise AssertionError(f"{page} still references external visual asset host {host}")
        if not re.search(r'<link rel="stylesheet" href="\./assets/fonts/fonts\.css(?:\?[^"]*)?">', content):
            raise AssertionError(f"{page} does not load the local font stylesheet")

    home = pages["index.html"]
    hero_picture = re.search(
        r'<picture class="hero-photo-picture"[^>]*>(.*?)</picture>',
        home,
        re.IGNORECASE | re.DOTALL,
    )
    if not hero_picture:
        raise AssertionError("Homepage hero must use a responsive picture element")
    hero_sources = re.findall(r"<source\b[^>]*>", hero_picture.group(1), re.IGNORECASE)
    hero_images = re.findall(r"<img\b[^>]*>", hero_picture.group(1), re.IGNORECASE)
    if len(hero_sources) != 1 or attr(hero_sources[0], "type") != "image/webp":
        raise AssertionError("Homepage hero is missing its responsive WebP source")
    if len(hero_images) != 1:
        raise AssertionError("Homepage hero picture must contain exactly one fallback image")
    hero = hero_images[0]
    if attr(hero, "fetchpriority") != "high" or attr(hero, "loading") != "eager":
        raise AssertionError("Homepage hero must remain eager-loaded with high fetch priority")
    if not attr(hero, "alt") or attr(hero, "width") != "1536" or attr(hero, "height") != "1159":
        raise AssertionError("Homepage hero needs descriptive alt text and intrinsic dimensions")
    if not attr(hero, "srcset") or not attr(hero_sources[0], "srcset") or not attr(hero, "sizes"):
        raise AssertionError("Homepage hero is missing responsive source candidates or sizes")
    for candidate in re.findall(r"(/?\.?/assets/photography/[^,\s]+)", attr(hero, "srcset") or ""):
        if not local_file(candidate).is_file():
            raise AssertionError(f"Homepage hero srcset references a missing image: {candidate}")

    preload = re.search(r'<link rel="preload" as="image"[^>]*>', home, re.IGNORECASE)
    if not preload or attr(preload.group(0), "fetchpriority") != "high":
        raise AssertionError("Homepage hero must be preloaded with high fetch priority")
    if not attr(preload.group(0), "imagesrcset") or not attr(preload.group(0), "imagesizes"):
        raise AssertionError("Homepage hero preload must match its responsive candidates")

    grid_start = home.find('<div class="gallery-grid"')
    grid_end = home.find('<p class="gallery-footnote"', grid_start)
    if grid_start < 0 or grid_end < 0:
        raise AssertionError("Homepage gallery grid or ending marker is missing")
    gallery = home[grid_start:grid_end]
    gallery_images = re.findall(r"<img\b[^>]*>", gallery, re.IGNORECASE)
    gallery_sources = re.findall(r"<source\b[^>]*>", gallery, re.IGNORECASE)
    if len(gallery_images) != 4 or len(gallery_sources) != 4:
        raise AssertionError("Homepage gallery must contain four responsive image pairs")
    for image in gallery_images:
        if attr(image, "loading") != "lazy" or attr(image, "decoding") != "async":
            raise AssertionError("Below-the-fold gallery images must remain lazy-loaded")
        if not attr(image, "alt") or not attr(image, "width") or not attr(image, "height"):
            raise AssertionError("Every gallery image needs descriptive alt text and intrinsic dimensions")
        if not attr(image, "srcset") or not attr(image, "sizes"):
            raise AssertionError("Every gallery fallback needs responsive srcset and sizes")
    for source in gallery_sources:
        if attr(source, "type") != "image/webp" or not attr(source, "srcset"):
            raise AssertionError("Every gallery image needs a responsive WebP source")

    full_res = re.findall(r'data-full="([^"]+)"', gallery)
    if len(full_res) != 4 or any("/assets/photography/originals/" not in item for item in full_res):
        raise AssertionError("Gallery lightbox must retain original full-resolution JPEG masters")

    for source in re.findall(r'url\(["\']?(\./assets/photography/[^"\')]+)', home):
        path = source.split("?", 1)[0]
        if not (ROOT / path.removeprefix("./")).is_file():
            raise AssertionError(f"Homepage CSS background references a missing local image: {source}")


def verify_security_policy() -> None:
    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    worker = (ROOT / "worker.mjs").read_text(encoding="utf-8")
    for label, content in (("_headers", headers), ("worker.mjs", worker)):
        if "fonts.googleapis.com" in content or "fonts.gstatic.com" in content:
            raise AssertionError(f"{label} CSP still allows Google Fonts hosts")
        if "style-src 'self' 'unsafe-inline'" not in content or "font-src 'self'" not in content:
            raise AssertionError(f"{label} CSP does not restrict styles and fonts to same-origin")

    fingerprint = (ROOT / "scripts/fingerprint_assets.py").read_text(encoding="utf-8")
    if "fonts.googleapis.com" in fingerprint or "fonts.gstatic.com" in fingerprint:
        raise AssertionError("Generated CSP template still allows Google Fonts hosts")


def main() -> None:
    verify_photography()
    verify_fonts()
    verify_pages_and_loading()
    verify_security_policy()
    print(
        "PASS self-hosted media: 4 untouched JPEG masters, 24 responsive image variants, "
        "6 optimized WOFF2 variable/static faces, 4 SIL OFL licenses, same-origin CSP, eager/high-priority hero, "
        "and lazy-loaded gallery thumbnails."
    )


if __name__ == "__main__":
    main()
