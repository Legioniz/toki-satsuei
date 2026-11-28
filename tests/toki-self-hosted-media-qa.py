#!/usr/bin/env python3
"""Verify TOKI's public photography and type are served from its own origin."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

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
CSS_BUNDLES = (
    "toki-home.css",
    "toki-archive.css",
    "toki-policies.css",
    "toki-404.css",
    "toki-admin.css",
    "toki-client.css",
)
REMOTE_VISUAL_HOSTS = (
    "media.base44.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)
EXPECTED_PHOTOS = {
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
EXPECTED_LICENSES = 4


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def url_hosts(content: str) -> set[str]:
    """Extract parsed URL hostnames; never treat arbitrary path text as a host."""
    candidates = re.findall(r'''https?://[^\s"'<>),;]+''', content, re.IGNORECASE)
    return {
        parsed.hostname.lower()
        for candidate in candidates
        if (parsed := urlsplit(candidate)).hostname
    }


def assert_no_remote_visual_hosts(content: str, label: str) -> None:
    forbidden = set(REMOTE_VISUAL_HOSTS)
    found = forbidden.intersection(url_hosts(content))
    if found:
        raise AssertionError(f"{label} contains remote visual asset origins: {', '.join(sorted(found))}")


def local_asset(public_path: str) -> Path:
    path = public_path.split("?", 1)[0].split("#", 1)[0]
    normalized = path.removeprefix("./").lstrip("/")
    target = (ROOT / normalized).resolve()
    if ROOT.resolve() not in target.parents:
        raise AssertionError(f"Asset path escapes repository root: {public_path}")
    if not target.is_file():
        raise AssertionError(f"Referenced asset does not exist: {public_path}")
    return target


def tag_attribute(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', tag, re.IGNORECASE)
    return match.group(1) if match else None


def srcset_paths(srcset: str) -> list[str]:
    return [entry.strip().split()[0] for entry in srcset.split(",") if entry.strip()]


def verify_photography() -> dict[str, dict]:
    manifest_path = ROOT / "assets/photography/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("photographs", [])
    if len(records) != len(EXPECTED_PHOTOS):
        raise AssertionError("Photography manifest must contain exactly four approved public images")

    by_slug: dict[str, dict] = {}
    for record in records:
        slug = record.get("slug")
        if slug not in EXPECTED_PHOTOS or slug in by_slug:
            raise AssertionError(f"Unexpected or duplicate photography entry: {slug!r}")
        expected_width, expected_height = EXPECTED_PHOTOS[slug]
        if (record.get("width"), record.get("height")) != (expected_width, expected_height):
            raise AssertionError(f"Unexpected original dimensions for {slug}")
        if abs(float(record.get("aspect_ratio", 0)) - expected_width / expected_height) > 0.00001:
            raise AssertionError(f"Incorrect aspect ratio in manifest for {slug}")
        if not isinstance(record.get("alt"), str) or not record["alt"].strip():
            raise AssertionError(f"Missing descriptive alt text for {slug}")

        original = local_asset(record["original"])
        original_bytes = original.read_bytes()
        if not original_bytes.startswith(b"\xff\xd8\xff"):
            raise AssertionError(f"Original master is not a JPEG: {original}")
        if len(original_bytes) != record.get("original_bytes"):
            raise AssertionError(f"Original master byte count changed: {slug}")
        if sha256(original_bytes) != record.get("original_sha256"):
            raise AssertionError(f"Original master checksum changed: {slug}")
        with Image.open(original) as image:
            image.verify()
        with Image.open(original) as image:
            oriented = ImageOps.exif_transpose(image)
            if image.format != "JPEG" or oriented.size != (expected_width, expected_height):
                raise AssertionError(f"Original master dimensions/encoding changed: {slug}")

        for variant_format, extension, image_format in (
            ("jpeg", ".jpg", "JPEG"),
            ("webp", ".webp", "WEBP"),
        ):
            variants = record.get("variants", {}).get(variant_format, [])
            if [item.get("width") for item in variants] != [480, 960, 1536]:
                raise AssertionError(f"{slug} must have 480, 960, and 1536px {variant_format} variants")
            for variant in variants:
                target = local_asset(variant["path"])
                payload = target.read_bytes()
                width = int(variant["width"])
                expected_variant_height = round(expected_height * width / expected_width)
                if target.suffix != extension or len(payload) != variant.get("bytes"):
                    raise AssertionError(f"Variant type or byte count mismatch: {target}")
                if sha256(payload) != variant.get("sha256"):
                    raise AssertionError(f"Variant checksum mismatch: {target}")
                if variant.get("height") != expected_variant_height:
                    raise AssertionError(f"Variant manifest dimensions incorrect: {target}")
                with Image.open(target) as image:
                    if image.format != image_format or image.size != (width, expected_variant_height):
                        raise AssertionError(f"Variant image dimensions/encoding incorrect: {target}")
        by_slug[slug] = record

    if set(by_slug) != set(EXPECTED_PHOTOS):
        raise AssertionError("Photography manifest is missing one or more approved images")
    return by_slug


def verify_fonts() -> None:
    root = ROOT / "assets/fonts"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    faces = manifest.get("fonts", [])
    if len(faces) != EXPECTED_FONT_FACES:
        raise AssertionError(f"Expected {EXPECTED_FONT_FACES} WOFF2 faces, found {len(faces)}")
    if {face.get("family") for face in faces} != EXPECTED_FONT_FAMILIES:
        raise AssertionError("Font manifest does not contain all four type families")
    for face in faces:
        font_path = local_asset(face["path"])
        payload = font_path.read_bytes()
        if not payload.startswith(b"wOF2"):
            raise AssertionError(f"Font binary is not WOFF2: {font_path}")
        if len(payload) != face.get("bytes") or sha256(payload) != face.get("sha256"):
            raise AssertionError(f"Font file checksum or size mismatch: {font_path}")

    license_files = sorted((root / "licenses").glob("*-OFL.txt"))
    if len(license_files) != EXPECTED_LICENSES:
        raise AssertionError("Expected four SIL Open Font License files")
    for license_file in license_files:
        if b"SIL OPEN FONT LICENSE" not in license_file.read_bytes().upper():
            raise AssertionError(f"Font license is not SIL OFL: {license_file}")

    font_css = (root / "fonts.css").read_text(encoding="utf-8")
    if font_css.count("@font-face") != EXPECTED_FONT_FACES:
        raise AssertionError("Local font stylesheet has an unexpected face count")
    if "font-display: swap" not in font_css:
        raise AssertionError("Local font stylesheet is missing font-display: swap")
    assert_no_remote_visual_hosts(font_css, "Local font stylesheet")
    for face in faces:
        filename = Path(face["path"]).name
        if f'url("/assets/fonts/{filename}")' not in font_css:
            raise AssertionError(f"Local font stylesheet omits {filename}")

    for bundle in CSS_BUNDLES:
        css = (ROOT / bundle).read_text(encoding="utf-8")
        if css.count("@font-face") != EXPECTED_FONT_FACES:
            raise AssertionError(f"{bundle} must bundle all local font faces")
        assert_no_remote_visual_hosts(css, bundle)
        if "font-display:swap" not in css:
            raise AssertionError(f"{bundle} is missing font-display: swap")
        for face in faces:
            if face["path"] not in css:
                raise AssertionError(f"{bundle} does not reference {face['path']}")


def verify_pages(photo_manifest: dict[str, dict]) -> None:
    content_by_page: dict[str, str] = {}
    for page in PUBLIC_PAGES:
        content = (ROOT / page).read_text(encoding="utf-8")
        content_by_page[page] = content
        assert_no_remote_visual_hosts(content, page)
        if not re.search(r'<link rel="stylesheet" href="\./toki-[^"]+\.css">', content):
            raise AssertionError(f"{page} is missing its generated page stylesheet")

    home = content_by_page["index.html"]
    hero_match = re.search(
        r'<picture class="hero-photo-picture"[^>]*>(.*?)</picture>',
        home,
        re.IGNORECASE | re.DOTALL,
    )
    if not hero_match:
        raise AssertionError("Homepage hero must use a responsive picture element")
    hero_source = re.search(r"<source\b[^>]*>", hero_match.group(1), re.IGNORECASE)
    hero_image = re.search(r"<img\b[^>]*>", hero_match.group(1), re.IGNORECASE)
    if not hero_source or not hero_image:
        raise AssertionError("Homepage hero picture needs a WebP source and fallback image")
    if tag_attribute(hero_source.group(0), "type") != "image/webp":
        raise AssertionError("Homepage hero source must use WebP")
    image = hero_image.group(0)
    if tag_attribute(image, "fetchpriority") != "high" or tag_attribute(image, "loading") != "eager":
        raise AssertionError("Homepage hero must remain eagerly loaded with high fetch priority")
    if tag_attribute(image, "width") != "1536" or tag_attribute(image, "height") != "1159":
        raise AssertionError("Homepage hero must declare its intrinsic dimensions")
    if not tag_attribute(image, "alt") or not tag_attribute(image, "sizes"):
        raise AssertionError("Homepage hero must include alt text and responsive sizing")
    if not tag_attribute(image, "srcset") or not tag_attribute(hero_source.group(0), "srcset"):
        raise AssertionError("Homepage hero is missing responsive JPEG/WebP candidates")
    for candidate in srcset_paths(tag_attribute(image, "srcset") or ""):
        local_asset(candidate)
    for candidate in srcset_paths(tag_attribute(hero_source.group(0), "srcset") or ""):
        local_asset(candidate)
    local_asset(tag_attribute(image, "src") or "")

    preload = re.search(r'<link rel="preload" as="image"[^>]*>', home, re.IGNORECASE)
    if not preload or tag_attribute(preload.group(0), "fetchpriority") != "high":
        raise AssertionError("Hero image must have a high-priority preload")
    preload_tag = preload.group(0)
    if not tag_attribute(preload_tag, "imagesrcset") or not tag_attribute(preload_tag, "imagesizes"):
        raise AssertionError("Hero preload must declare responsive candidates and sizes")
    if not (tag_attribute(preload_tag, "href") or "").endswith(".webp"):
        raise AssertionError("Hero preload should use the WebP candidate")

    grid_start = home.find('<div class="gallery-grid"')
    grid_end = home.find('<p class="gallery-footnote"', grid_start)
    if grid_start < 0 or grid_end < 0:
        raise AssertionError("Homepage gallery boundaries are missing")
    gallery = home[grid_start:grid_end]
    pictures = re.findall(r"<picture\b[^>]*>(.*?)</picture>", gallery, re.IGNORECASE | re.DOTALL)
    if len(pictures) != 4:
        raise AssertionError("Homepage gallery must use four responsive picture elements")
    for index, picture in enumerate(pictures, start=1):
        source = re.search(r"<source\b[^>]*>", picture, re.IGNORECASE)
        image = re.search(r"<img\b[^>]*>", picture, re.IGNORECASE)
        if not source or not image:
            raise AssertionError(f"Gallery image {index} is missing its WebP source or JPEG fallback")
        if tag_attribute(source.group(0), "type") != "image/webp":
            raise AssertionError(f"Gallery image {index} has a non-WebP source")
        if tag_attribute(image.group(0), "loading") != "lazy":
            raise AssertionError(f"Below-the-fold gallery image {index} must be lazy-loaded")
        if tag_attribute(image.group(0), "decoding") != "async":
            raise AssertionError(f"Gallery image {index} must use async decoding")
        if not all(tag_attribute(image.group(0), key) for key in ("alt", "width", "height", "srcset", "sizes")):
            raise AssertionError(f"Gallery image {index} is missing alt, dimension, or responsive attributes")
        local_asset(tag_attribute(image.group(0), "src") or "")
        for candidate in srcset_paths(tag_attribute(image.group(0), "srcset") or ""):
            local_asset(candidate)
        for candidate in srcset_paths(tag_attribute(source.group(0), "srcset") or ""):
            local_asset(candidate)

    full_resolution = re.findall(r'data-full="([^"]+)"', gallery)
    expected_full = {item["original"] for item in photo_manifest.values()}
    if len(full_resolution) != 4 or set(full_resolution) != expected_full:
        raise AssertionError("Gallery lightbox must point to the four untouched full-resolution masters")
    for source in re.findall(r'url\(["\']?(/assets/photography/[^"\')]+)', home):
        local_asset(source)


def verify_content_security_policy() -> None:
    sources = {
        "_headers": (ROOT / "_headers").read_text(encoding="utf-8"),
        "worker.mjs": (ROOT / "worker.mjs").read_text(encoding="utf-8"),
        "fingerprint_assets.py": (ROOT / "scripts/fingerprint_assets.py").read_text(encoding="utf-8"),
    }
    for name, content in sources.items():
        assert_no_remote_visual_hosts(content, name)
        if "style-src 'self' 'unsafe-inline'" not in content or "font-src 'self'" not in content:
            raise AssertionError(f"{name} does not restrict CSS/font resources to the site origin")


def main() -> None:
    photos = verify_photography()
    verify_fonts()
    verify_pages(photos)
    verify_content_security_policy()
    print(
        "PASS self-hosted visual assets: 4 untouched JPEG masters, 24 responsive image variants, "
        "6 local WOFF2 faces, 4 SIL OFL licenses, same-origin CSP, high-priority eager hero, "
        "and lazy-loaded gallery images."
    )


if __name__ == "__main__":
    main()
