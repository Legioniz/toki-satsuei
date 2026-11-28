#!/usr/bin/env python3
"""Verify TOKI's same-origin photography and web-font delivery contract."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from html.parser import HTMLParser
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
DISALLOWED_VISUAL_ASSET_HOSTS = frozenset({
    "media.base44.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
})
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


class VisualAssetURLCollector(HTMLParser):
    """Collect actual image/font URL references without scanning prose or link text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        for name in ("src", "poster", "data-full", "imagesrc", "imagesrcset"):
            value = values.get(name, "")
            if value:
                self._add_candidates(value)
        if tag.lower() in {"img", "source"}:
            self._add_candidates(values.get("srcset", ""))
        if tag.lower() == "meta" and values.get("property", "").lower() in {
            "og:image", "og:image:url", "twitter:image",
        }:
            self._add_candidates(values.get("content", ""))
        if tag.lower() == "link":
            rel = set(values.get("rel", "").lower().split())
            if rel.intersection({"stylesheet", "preload", "icon"}):
                self._add_candidates(values.get("href", ""))
        style = values.get("style", "")
        if style:
            self._add_css_urls(style)
        if tag.lower() == "style":
            self.in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self._add_css_urls(data)

    def _add_css_urls(self, css: str) -> None:
        for match in re.finditer(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", css, re.IGNORECASE):
            self._add_candidates(match.group(2))

    def _add_candidates(self, value: str) -> None:
        for candidate in value.split(","):
            url = candidate.strip().split()[0] if candidate.strip() else ""
            if url:
                self.urls.append(url)


def is_disallowed_visual_asset_url(value: str) -> bool:
    parsed = urlsplit(value.strip())
    hostname = (parsed.hostname or "").lower()
    return hostname in DISALLOWED_VISUAL_ASSET_HOSTS


def css_url_values(css: str) -> list[str]:
    return [
        match.group(2).strip()
        for match in re.finditer(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", css, re.IGNORECASE)
    ]


def parse_csp_directives(policy: str) -> dict[str, list[str]]:
    directives: dict[str, list[str]] = {}
    for segment in policy.split(";"):
        tokens = segment.strip().split()
        if tokens:
            directives[tokens[0].lower()] = tokens[1:]
    return directives


def csp_from_fingerprint_source(source: str) -> str:
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CSP_META"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise AssertionError("Fingerprint build source does not define a literal CSP_META policy")


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
    importer_source = (ROOT / "scripts/import_site_media.py").read_text(encoding="utf-8")
    if re.search(
        r"""(?:url\(\s*['"]?/assets/fonts/|["']path["']\s*:\s*["']/assets/fonts/)""",
        importer_source,
    ):
        raise AssertionError(
            "Font importer must emit ./assets/fonts URLs for GitHub Pages project-subpath hosting"
        )
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

    shared_css = (root / "fonts.css").read_text(encoding="utf-8")
    caveat_css = (root / "fonts-caveat.css").read_text(encoding="utf-8")
    if shared_css.count("@font-face") != 5 or caveat_css.count("@font-face") != 1:
        raise AssertionError("Shared and handwritten font CSS must contain five and one faces respectively")
    for css in (shared_css, caveat_css):
        if "font-display: swap" not in css:
            raise AssertionError("Font CSS is missing font-display: swap")
        for reference in css_url_values(css):
            parsed = urlsplit(reference)
            if (
                parsed.scheme
                or parsed.netloc
                or not parsed.path.startswith("./assets/fonts/")
                or is_disallowed_visual_asset_url(reference)
            ):
                raise AssertionError(f"Font CSS contains a non-local font URL: {reference}")
    for item in fonts:
        filename = Path(item["path"]).name
        source_css = caveat_css if item.get("family") == "Caveat" else shared_css
        if f'url("./assets/fonts/{filename}")' not in source_css:
            raise AssertionError(f"Font CSS source does not declare local face: {filename}")

    bundle_face_counts = {
        "toki-home.css": 6,
        "toki-archive.css": 5,
        "toki-policies.css": 5,
        "toki-404.css": 6,
        "toki-admin.css": 5,
        "toki-client.css": 5,
    }
    for bundle_name, expected_count in bundle_face_counts.items():
        bundle = (ROOT / bundle_name).read_text(encoding="utf-8")
        if bundle.count("@font-face") != expected_count or "font-display:swap" not in bundle:
            raise AssertionError(f"{bundle_name} has an unexpected local font-face inventory")
        for item in fonts:
            filename = Path(item["path"]).name
            family = item.get("family")
            expected_here = family != "Caveat" or bundle_name in ("toki-home.css", "toki-404.css")
            if expected_here and f'url("./assets/fonts/{filename}")' not in bundle:
                raise AssertionError(f"{bundle_name} is missing the local font resource: {filename}")
            if not expected_here and filename in bundle:
                raise AssertionError(f"{bundle_name} unnecessarily declares the Caveat font")


def verify_pages_and_loading() -> None:
    pages: dict[str, str] = {}
    for page in PUBLIC_PAGES:
        content = (ROOT / page).read_text(encoding="utf-8")
        pages[page] = content
        collector = VisualAssetURLCollector()
        collector.feed(content)
        for reference in collector.urls:
            if is_disallowed_visual_asset_url(reference):
                raise AssertionError(f"{page} still references a retired visual asset origin: {reference}")
            parsed_reference = urlsplit(reference.strip())
            if (
                not parsed_reference.scheme
                and not parsed_reference.netloc
                and parsed_reference.path.startswith("/")
            ):
                raise AssertionError(
                    f"{page} uses a root-absolute URL that escapes the GitHub Pages "
                    f"repository subpath: {reference}"
                )
        expected_bundle = {
            "index.html": "toki-home.css",
            "booking.html": "toki-home.css",
            "library.html": "toki-archive.css",
            "policies.html": "toki-policies.css",
            "404.html": "toki-404.css",
            "admin.html": "toki-admin.css",
            "client-gallery.html": "toki-client.css",
        }[page]
        stylesheets = re.findall(r'<link rel="stylesheet" href="([^"]+)">', content)
        if stylesheets != [f"./{expected_bundle}"]:
            raise AssertionError(f"{page} must load exactly one page-scoped CSS bundle, found {stylesheets}")

    # GitHub Pages project sites are hosted below /<repository>/.
    # Any root-absolute CSS URL would jump to the domain root and break assets.
    for bundle_name in (
        "toki-home.css",
        "toki-archive.css",
        "toki-policies.css",
        "toki-404.css",
        "toki-admin.css",
        "toki-client.css",
    ):
        bundle = (ROOT / bundle_name).read_text(encoding="utf-8")
        for reference in css_url_values(bundle):
            parsed_reference = urlsplit(reference.strip())
            if (
                not parsed_reference.scheme
                and not parsed_reference.netloc
                and parsed_reference.path.startswith("/")
            ):
                raise AssertionError(
                    f"{bundle_name} contains a root-absolute CSS asset URL: {reference}"
                )

    for manifest_path in ("assets/fonts/manifest.json", "assets/photography/manifest.json"):
        manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
        serialized = json.dumps(manifest)
        if re.search(r'(?<!:)"/assets/', serialized):
            raise AssertionError(
                f"{manifest_path} contains a root-absolute asset path that breaks GitHub Pages subpath hosting"
            )

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

    image_preloads = re.findall(r'<link rel="preload" as="image"[^>]*>', home, re.IGNORECASE)
    hero_preload = next(
        (tag for tag in image_preloads if attr(tag, "href") == "./assets/photography/behind-the-camera-960.webp"),
        None,
    )
    if not hero_preload or attr(hero_preload, "fetchpriority") != "high":
        raise AssertionError("Homepage hero WebP source must be preloaded with high fetch priority")
    if attr(hero_preload, "type") != "image/webp":
        raise AssertionError("Homepage hero preload must use the same format as its responsive picture source")
    if attr(hero_preload, "imagesrcset") != attr(hero_sources[0], "srcset"):
        raise AssertionError("Homepage hero preload must match the responsive WebP candidates")
    if attr(hero_preload, "imagesizes") != attr(hero_sources[0], "sizes"):
        raise AssertionError("Homepage hero preload sizes must match its responsive picture source")

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
    header_policy = re.search(r"(?im)^\s*Content-Security-Policy:\s*(.+)$", headers)
    worker_policy = re.search(r'"Content-Security-Policy"\s*:\s*"([^"]+)"', worker)
    if not header_policy or not worker_policy:
        raise AssertionError("Pages and Worker CSP policies must both be present")
    fingerprint_source = (ROOT / "scripts/fingerprint_assets.py").read_text(encoding="utf-8")
    policies = (
        ("_headers", header_policy.group(1).strip()),
        ("worker.mjs", worker_policy.group(1).strip()),
        ("fingerprint CSP", csp_from_fingerprint_source(fingerprint_source)),
    )
    for label, policy in policies:
        directives = parse_csp_directives(policy)
        style_sources = directives.get("style-src", [])
        font_sources = directives.get("font-src", [])
        if set(style_sources) != {"'self'", "'unsafe-inline'"}:
            raise AssertionError(f"{label} style-src must allow only same-origin styles and inline style attributes")
        if font_sources != ["'self'"]:
            raise AssertionError(f"{label} font-src must allow only same-origin font resources")

    fonts_css = (ROOT / "assets/fonts/fonts.css").read_text(encoding="utf-8")
    for reference in css_url_values(fonts_css):
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith("./assets/fonts/"):
            raise AssertionError(
                "Generated font CSS must use repository-subpath-safe relative URLs, "
                f"got {reference!r}"
            )


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
