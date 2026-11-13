#!/usr/bin/env python3
"""Verify that every TOKI SATSUEI page asset and runtime dependency is connected."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "library.html", "policies.html", "404.html")
WORKFLOW = ROOT / ".github/workflows/deploy.yml"
EXPECTED_CONSUMERS = {
    "index.html": ("motion-system.js", "site.js", "facebook-feed.js"),
    "library.html": ("motion-system.js", "site.js", "library.js"),
    "policies.html": ("motion-system.js", "site.js"),
    "404.html": (),
}
EXPECTED_DATA = {
    "facebook-posts.json": "facebook-feed.js",
    "media-library.json": "library.js",
}


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local: list[str] = []
        self.styles: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("href", "src", "poster"):
            value = values.get(key)
            if not value:
                continue
            path = local_path(value, Path("."))
            if path:
                self.local.append(path)
                if tag == "link" and key == "href" and values.get("rel") == "stylesheet":
                    self.styles.append(path)
                if tag == "script" and key == "src":
                    self.scripts.append(path)


def local_path(value: str, base: Path) -> str | None:
    value = value.strip()
    parsed = urlsplit(value)
    if not parsed.path or parsed.scheme or parsed.netloc or value.startswith("//"):
        return None
    path = unquote(parsed.path)
    resolved = (ROOT / path.lstrip("/")).resolve() if path.startswith("/") else (ROOT / base / path).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise AssertionError(f"Local reference escapes the repository: {value}") from error


def verify_media_manifest(failures: list[str]) -> None:
    path = ROOT / "media-library.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"Archive manifest is not valid JSON: {error}")
        return
    if manifest.get("schema_version") != 2:
        failures.append("Archive manifest must use schema version 2")
    seen: set[str] = set()
    for category in manifest.get("categories", []):
        category_id = category.get("id", "")
        if not category_id or category_id in seen:
            failures.append(f"Archive category id is missing or duplicated: {category_id!r}")
            continue
        seen.add(category_id)
        if not (ROOT / "media-library" / category_id).is_dir():
            failures.append(f"Archive category has no upload folder: {category_id}")
        albums = category.get("albums", [])
        if int(category.get("album_count", -1)) != len(albums):
            failures.append(f"Album count does not match the manifest for {category_id}")
        images = videos = media_total = 0
        for album in albums:
            media = album.get("media", [])
            for item in media:
                kind = item.get("type")
                if kind not in ("image", "video"):
                    failures.append(f"Unsupported media type in {category_id}: {kind!r}")
                images += kind == "image"
                videos += kind == "video"
                media_total += 1
                source = item.get("src", "")
                target = local_path(source, Path("."))
                if not target or not (ROOT / target).is_file():
                    failures.append(f"Archive media path is missing: {source}")
        expected = {
            "image_count": images,
            "video_count": videos,
            "media_count": media_total,
        }
        for key, value in expected.items():
            if int(category.get(key, -1)) != value:
                failures.append(f"{category_id}.{key} is {category.get(key)!r}; expected {value}")


def main() -> None:
    failures: list[str] = []
    page_refs: dict[str, References] = {}
    for page in PAGES:
        parser = References()
        parser.feed((ROOT / page).read_text(encoding="utf-8"))
        page_refs[page] = parser
        for target in parser.local:
            if not (ROOT / target).is_file():
                failures.append(f"{page} references missing local file: {target}")
        if len(parser.scripts) != len(set(parser.scripts)):
            failures.append(f"{page} loads a script more than once")
        expected = EXPECTED_CONSUMERS[page]
        actual = tuple(script for script in parser.scripts if script in expected)
        if actual != expected or len(parser.scripts) != len(expected):
            failures.append(f"{page} has an incomplete or unexpected controller stack: {parser.scripts}")
        if page != "404.html" and "motion-system.css" not in parser.styles:
            failures.append(f"{page} is missing the shared motion stylesheet")

    linked_styles = {asset for refs in page_refs.values() for asset in refs.styles}
    linked_scripts = {asset for refs in page_refs.values() for asset in refs.scripts}
    for asset in sorted(path.name for path in ROOT.glob("*.css")):
        if asset not in linked_styles:
            failures.append(f"Unreferenced production stylesheet: {asset}")
    for asset in sorted(path.name for path in ROOT.glob("*.js")):
        if asset not in linked_scripts:
            failures.append(f"Unreferenced production script: {asset}")

    for stylesheet in linked_styles:
        source = (ROOT / stylesheet).read_text(encoding="utf-8")
        pattern = r"""url\(\s*(['"]?)(.*?)\1\s*\)"""
        for match in re.finditer(pattern, source, re.IGNORECASE):
            target = local_path(match.group(2), Path(stylesheet).parent)
            if target and not (ROOT / target).is_file():
                failures.append(f"{stylesheet} references missing local asset: {target}")

    script_sources = {name: (ROOT / name).read_text(encoding="utf-8") for name in linked_scripts}
    for data_file, consumer in EXPECTED_DATA.items():
        if data_file not in script_sources.get(consumer, ""):
            failures.append(f"{consumer} no longer references its data source {data_file}")
        if not (ROOT / data_file).is_file():
            failures.append(f"Missing runtime data source: {data_file}")

    verify_media_manifest(failures)

    workflow = WORKFLOW.read_text(encoding="utf-8")
    for test_file in sorted((ROOT / "tests").glob("*.py")):
        if f"python tests/{test_file.name}" not in workflow:
            failures.append(f"QA script is not wired into GitHub Actions: {test_file.name}")
    package_line = next(
        (line for line in workflow.splitlines() if re.search(r"\bcp\s+index\.html\b", line) and "dist/" in line),
        "",
    )
    if not package_line:
        failures.append("Pages artifact copy command is missing")
    else:
        package_items = set(package_line.split()[1:-1])
        required = {
            "index.html", "library.html", "policies.html", "404.html",
            *linked_styles, *linked_scripts, *EXPECTED_DATA, "robots.txt", "sitemap.xml",
        }
        missing = sorted(required - package_items)
        if missing:
            failures.append("Pages artifact omits required runtime files: " + ", ".join(missing))
    if "cp -R media-library dist/" not in workflow:
        failures.append("Pages artifact does not include the uploadable media-library shelves")
    for asset in ("site.js", "library.js", "library.css", "cinematic.css", "motion-system.css"):
        if f"test -s dist/{asset}" not in workflow:
            failures.append(f"Pages artifact does not assert that {asset} was packaged")

    if failures:
        raise SystemExit("FAIL TOKI SATSUEI asset integration QA:\n- " + "\n- ".join(failures))
    print(
        "PASS TOKI SATSUEI asset integration QA: "
        f"{len(PAGES)} pages, {len(linked_styles)} stylesheets, "
        f"{len(linked_scripts)} scripts, {len(EXPECTED_DATA)} data sources, "
        "validated archive media counts, and a complete Pages package."
    )


if __name__ == "__main__":
    main()
