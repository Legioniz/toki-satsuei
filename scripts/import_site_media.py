#!/usr/bin/env python3
"""Import TOKI's approved public photography and Google Fonts into same-origin assets.

Original JPEG masters are copied byte-for-byte and never replaced. Responsive
JPEG/WebP derivatives and font files are generated beside those masters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PHOTOGRAPHY_ROOT = ROOT / "assets" / "photography"
FONT_ROOT = ROOT / "assets" / "fonts"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_FONT_BYTES = 4 * 1024 * 1024
MAX_CSS_BYTES = 512 * 1024
TARGET_WIDTHS = (480, 960, 1536)

PHOTOGRAPHS = (
    {
        "slug": "behind-the-camera",
        "title": "Behind the camera",
        "alt": "Photographer holding a Canon camera, ready to capture a moment",
        "width": 1536,
        "height": 1159,
        "source": "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/3db8c3355_242599.jpg",
    },
    {
        "slug": "between-turns",
        "title": "Between turns",
        "alt": "Pool table detail with a cue and billiard balls",
        "width": 1536,
        "height": 1024,
        "source": "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/b21ff20c7_242600.jpg",
    },
    {
        "slug": "colour-in-the-quiet",
        "title": "Colour in the quiet",
        "alt": "Close detail of a billiards table, showing the felt texture and colour",
        "width": 1536,
        "height": 1024,
        "source": "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/e03bfd350_242598.jpg",
    },
    {
        "slug": "before-the-next-shot",
        "title": "Before the next shot",
        "alt": "Billiard balls arranged on a table before the next shot",
        "width": 1536,
        "height": 1024,
        "source": "https://media.base44.com/images/public/6af6b70d3bc15f40b706af32/52f603569_242601.jpg",
    },
)

FONT_CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Caveat:wght@400..700&"
    "family=Cormorant+Garamond:ital,wght@0,400..700;1,400..600&"
    "family=DM+Sans:wght@400..700&"
    "family=Space+Mono:wght@400;700&display=swap"
)

FONT_SPECS = {
    "Caveat": {
        "slug": "caveat",
        "license_dir": "caveat",
        "faces": [("normal", "400 700")],
    },
    "Cormorant Garamond": {
        "slug": "cormorant-garamond",
        "license_dir": "cormorantgaramond",
        "faces": [("normal", "400 700"), ("italic", "400 600")],
    },
    "DM Sans": {
        "slug": "dm-sans",
        "license_dir": "dmsans",
        "faces": [("normal", "400 700")],
    },
    "Space Mono": {
        "slug": "space-mono",
        "license_dir": "spacemono",
        "faces": [("normal", "400"), ("normal", "700")],
    },
}

EXPECTED_FONT_FACES = {
    (family, style, weight)
    for family, spec in FONT_SPECS.items()
    for style, weight in spec["faces"]
}


def fetch_bytes(url: str, limit: int) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Refusing non-HTTPS asset URL: {url}")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(request, timeout=45) as response:
            final_host = urlparse(response.geturl()).hostname
            if final_host not in {"media.base44.com", "fonts.googleapis.com", "fonts.gstatic.com", "raw.githubusercontent.com"}:
                raise ValueError(f"Unexpected asset redirect host: {final_host}")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > limit:
                raise ValueError(f"Asset exceeds size limit ({content_length} bytes): {url}")
            payload = response.read(limit + 1)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Unable to retrieve required asset: {url} ({error})") from error
    if len(payload) > limit:
        raise ValueError(f"Asset exceeds size limit ({limit} bytes): {url}")
    if not payload:
        raise ValueError(f"Empty response for asset: {url}")
    return payload


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_master(photo: dict) -> tuple[Path, Image.Image, bytes]:
    master = PHOTOGRAPHY_ROOT / "originals" / f'{photo["slug"]}.jpg'
    if not master.is_file():
        payload = fetch_bytes(photo["source"], MAX_IMAGE_BYTES)
        if not payload.startswith(b"\xff\xd8\xff"):
            raise ValueError(f"Master is not a JPEG: {photo['slug']}")
        with Image.open(__import__("io").BytesIO(payload)) as check:
            check.verify()
        atomic_write(master, payload)

    original_bytes = master.read_bytes()
    if not original_bytes.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"Stored original is not a JPEG: {master}")
    with Image.open(master) as opened:
        opened.verify()
    with Image.open(master) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    if image.size != (photo["width"], photo["height"]):
        raise ValueError(
            f'Unexpected master dimensions for {photo["slug"]}: '
            f'{image.width}x{image.height}; expected {photo["width"]}x{photo["height"]}'
        )
    return master, image, original_bytes


def build_photography() -> list[dict]:
    manifest = []
    for photo in PHOTOGRAPHS:
        master, image, original_bytes = load_master(photo)
        variants = {"jpeg": [], "webp": []}
        for target_width in TARGET_WIDTHS:
            if target_width > image.width:
                continue
            target_height = round(image.height * target_width / image.width)
            resized = image if target_width == image.width else image.resize(
                (target_width, target_height), Image.Resampling.LANCZOS
            )
            icc_profile = image.info.get("icc_profile")
            for format_name, extension in (("jpeg", "jpg"), ("webp", "webp")):
                output = PHOTOGRAPHY_ROOT / f'{photo["slug"]}-{target_width}.{extension}'
                options = (
                    {"format": "JPEG", "quality": 88, "optimize": True, "progressive": True, "subsampling": 0}
                    if format_name == "jpeg"
                    else {"format": "WEBP", "quality": 86, "method": 6}
                )
                if icc_profile:
                    options["icc_profile"] = icc_profile
                with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as temporary:
                    temporary_path = Path(temporary.name)
                try:
                    resized.save(temporary_path, **options)
                    atomic_write(output, temporary_path.read_bytes())
                finally:
                    temporary_path.unlink(missing_ok=True)
                with Image.open(output) as check:
                    if check.size != (target_width, target_height):
                        raise ValueError(f"Variant dimensions are incorrect: {output}")
                    if check.format != ("JPEG" if format_name == "jpeg" else "WEBP"):
                        raise ValueError(f"Variant encoding is incorrect: {output}")
                variants[format_name].append(
                    {
                        "width": target_width,
                        "height": target_height,
                        "path": f"/assets/photography/{output.name}",
                        "bytes": output.stat().st_size,
                        "sha256": sha256(output.read_bytes()),
                    }
                )

        manifest.append(
            {
                "slug": photo["slug"],
                "title": photo["title"],
                "alt": photo["alt"],
                "original": f"/assets/photography/originals/{master.name}",
                "width": image.width,
                "height": image.height,
                "aspect_ratio": round(image.width / image.height, 6),
                "original_bytes": len(original_bytes),
                "original_sha256": sha256(original_bytes),
                "variants": variants,
            }
        )

    payload = json.dumps(
        {"version": 1, "hosting": "same-origin Cloudflare Pages", "photographs": manifest},
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    atomic_write(PHOTOGRAPHY_ROOT / "manifest.json", payload.encode("utf-8"))
    return manifest


def parse_font_faces(css: str) -> dict[tuple[str, str, str], str]:
    """Resolve the requested static font faces from modern-browser Google CSS.

    Google Fonts varies its CSS response by User-Agent. A real browser User-Agent
    is required to receive WOFF2 rather than legacy TTF sources. Match each
    descriptor independently and accept either quoted or unquoted WOFF2 URLs.
    """
    selected: dict[tuple[str, str, str], str] = {}
    diagnostics: set[str] = set()
    for match in re.finditer(r"@font-face\s*\{([^}]+)\}", css, re.IGNORECASE | re.DOTALL):
        block = match.group(1)
        family_match = re.search(r"font-family:\s*['\"]?([^;'\"}\n]+)['\"]?\s*;", block, re.IGNORECASE)
        style_match = re.search(r"font-style:\s*([^;]+)", block, re.IGNORECASE)
        weight_match = re.search(r"font-weight:\s*([^;]+)", block, re.IGNORECASE)
        range_match = re.search(r"unicode-range:\s*([^;]+)", block, re.IGNORECASE)
        source_match = re.search(
            r"""src:\s*url\(\s*['"]?(https://fonts\.gstatic\.com/[^)'"\s]+)['"]?\s*\)\s*format\(\s*['"]?woff2['"]?\s*\)""",
            block,
            re.IGNORECASE,
        )
        if family_match:
            family = family_match.group(1).strip()
            if family in FONT_SPECS:
                weight_text = weight_match.group(1).strip() if weight_match else "?"
                style_text = style_match.group(1).strip().lower() if style_match else "?"
                diagnostics.add(f"{family} {style_text} {weight_text}")
        if not all((family_match, style_match, weight_match, range_match, source_match)):
            continue
        family = family_match.group(1).strip()
        style = style_match.group(1).strip().lower()
        weight = weight_match.group(1).strip()
        if family not in FONT_SPECS:
            continue
        if not re.search(r"U\+\s*0000\s*-\s*00FF", range_match.group(1), re.IGNORECASE):
            continue
        key = (family, style, weight)
        if key in EXPECTED_FONT_FACES:
            selected[key] = source_match.group(1)

    missing = EXPECTED_FONT_FACES - selected.keys()
    if missing:
        readable = ", ".join(f"{family} {style} {weight}" for family, style, weight in sorted(missing))
        received = ", ".join(sorted(diagnostics)) or "no matching @font-face blocks"
        raise ValueError(
            "Google Fonts CSS did not provide all required Latin WOFF2 faces: "
            f"{readable}. Received descriptors: {received}"
        )
    return selected

def font_filename(spec: dict, style: str, weight: str) -> str:
    suffix = "italic" if style == "italic" else "normal"
    weight_label = "variable" if " " in weight else weight
    return f'{spec["slug"]}-{weight_label}-{suffix}.woff2'


def build_fonts() -> dict:
    expected_files = []
    for family, spec in FONT_SPECS.items():
        for style, weight in spec["faces"]:
            filename = font_filename(spec, style, weight)
            expected_files.append((family, style, weight, filename))

    missing = [
        item for item in expected_files
        if not (FONT_ROOT / item[3]).is_file()
    ]
    urls: dict[tuple[str, str, str], str] = {}
    if missing:
        css_bytes = fetch_bytes(FONT_CSS_URL, MAX_CSS_BYTES)
        urls = parse_font_faces(css_bytes.decode("utf-8"))

    font_records = []
    for family, style, weight, filename in expected_files:
        path = FONT_ROOT / filename
        if not path.is_file():
            key = (family, style, weight)
            payload = fetch_bytes(urls[key], MAX_FONT_BYTES)
            if not payload.startswith(b"wOF2"):
                raise ValueError(f"Expected a WOFF2 file for {family} {weight} {style}")
            atomic_write(path, payload)
        payload = path.read_bytes()
        if not payload.startswith(b"wOF2"):
            raise ValueError(f"Stored font is not WOFF2: {path}")
        font_records.append(
            {
                "family": family,
                "style": style,
                "weight": weight if " " in weight else int(weight),
                "path": f"/assets/fonts/{filename}",
                "bytes": len(payload),
                "sha256": sha256(payload),
            }
        )

    for spec in FONT_SPECS.values():
        license_path = FONT_ROOT / "licenses" / f'{spec["slug"]}-OFL.txt'
        if not license_path.is_file():
            url = f'https://raw.githubusercontent.com/google/fonts/main/ofl/{spec["license_dir"]}/OFL.txt'
            license_payload = fetch_bytes(url, MAX_FONT_BYTES)
            if b"SIL OPEN FONT LICENSE" not in license_payload.upper():
                raise ValueError(f"Font license is not SIL OFL: {license_path}")
            atomic_write(license_path, license_payload)

    css_lines = [
        "/* Self-hosted Latin WOFF2 variable faces and static technical weights. */",
        "",
    ]
    for family, style, weight, filename in expected_files:
        css_lines.extend(
            [
                "@font-face {",
                f'  font-family: "{family}";',
                f"  font-style: {style};",
                f"  font-weight: {weight};",
                "  font-display: swap;",
                f'  src: url("./{filename}") format("woff2");',
                "}",
                "",
            ]
        )
    atomic_write(FONT_ROOT / "fonts.css", "\n".join(css_lines).encode("utf-8"))

    # Remove stale per-weight duplicates from the previous static-face importer.
    expected_names = {item[3] for item in expected_files}
    for stale in FONT_ROOT.glob("*.woff2"):
        if stale.name not in expected_names:
            stale.unlink()

    manifest = {
        "version": 2,
        "source": "Google Fonts CSS2 API, imported for self-hosting",
        "format": "WOFF2",
        "font_display": "swap",
        "fonts": font_records,
    }
    atomic_write(
        FONT_ROOT / "manifest.json",
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    return manifest

def verify_assets() -> None:
    for photo in PHOTOGRAPHS:
        master = PHOTOGRAPHY_ROOT / "originals" / f'{photo["slug"]}.jpg'
        if not master.is_file():
            raise FileNotFoundError(f"Missing original master: {master}")
        with Image.open(master) as source:
            source.verify()
        with Image.open(master) as source:
            oriented = ImageOps.exif_transpose(source)
            if oriented.size != (photo["width"], photo["height"]):
                raise ValueError(f"Original master dimensions changed: {master}")
        for width in TARGET_WIDTHS:
            if width > photo["width"]:
                continue
            height = round(photo["height"] * width / photo["width"])
            for extension, expected_format in (("jpg", "JPEG"), ("webp", "WEBP")):
                variant = PHOTOGRAPHY_ROOT / f'{photo["slug"]}-{width}.{extension}'
                with Image.open(variant) as image:
                    if image.format != expected_format or image.size != (width, height):
                        raise ValueError(f"Invalid image variant: {variant}")
    expected_font_names = set()
    for family, spec in FONT_SPECS.items():
        for style, weight in spec["faces"]:
            font = FONT_ROOT / font_filename(spec, style, weight)
            expected_font_names.add(font.name)
            if not font.is_file() or not font.read_bytes().startswith(b"wOF2"):
                raise ValueError(f"Missing or invalid self-hosted font: {font}")
    actual_font_names = {font.name for font in FONT_ROOT.glob("*.woff2")}
    if actual_font_names != expected_font_names:
        raise ValueError(
            f"Self-hosted font set contains unexpected files: "
            f"{sorted(actual_font_names ^ expected_font_names)}"
        )
        license_path = FONT_ROOT / "licenses" / f'{spec["slug"]}-OFL.txt'
        if not license_path.is_file() or b"SIL OPEN FONT LICENSE" not in license_path.read_bytes().upper():
            raise ValueError(f"Missing SIL Open Font License: {license_path}")
    css = (FONT_ROOT / "fonts.css").read_text(encoding="utf-8")
    if "fonts.gstatic.com" in css or "https://" in css or "font-display: swap" not in css:
        raise ValueError("Generated font CSS contains a remote source or lacks font-display: swap")
    manifest = json.loads((PHOTOGRAPHY_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest.get("photographs", [])) != len(PHOTOGRAPHS):
        raise ValueError("Photography manifest is incomplete")
    print(f"PASS self-hosted media: 4 untouched JPEG masters, 24 responsive derivatives, {sum(len(spec['faces']) for spec in FONT_SPECS.values())} WOFF2 faces, and 4 OFL licenses.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify imported assets without network access.")
    args = parser.parse_args()
    if args.verify_only:
        verify_assets()
        return
    photography = build_photography()
    fonts = build_fonts()
    verify_assets()
    print(
        f'Imported {len(photography)} photography masters with responsive variants '
        f'and {len(fonts["fonts"])} local font faces.'
    )


if __name__ == "__main__":
    main()
