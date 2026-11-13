#!/usr/bin/env python3
"""Refresh a public TOKI SATSUEI Page-post snapshot using Meta's official Graph API.

The Page access token is read only from the process environment. It is never
written to the generated JSON or printed to the workflow log.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


API_VERSION = "v27.0"
PAGE_NAME = "TOKI SATSUEI"
PAGE_URL = "https://www.facebook.com/tokisatsuiephotography/"
POST_LIMIT = 8


def read_snapshot(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_snapshot(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(rendered, encoding="utf-8")


def valid_facebook_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        return ""
    return value


def image_from_post(post: dict) -> str:
    candidate = post.get("full_picture")
    if isinstance(candidate, str) and candidate.startswith("https://"):
        return candidate
    attachments = post.get("attachments")
    if isinstance(attachments, dict):
        queue = list(attachments.get("data", []))
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            media = item.get("media")
            if isinstance(media, dict):
                image = media.get("image")
                if isinstance(image, dict):
                    source = image.get("src")
                    if isinstance(source, str) and source.startswith("https://"):
                        return source
            nested = item.get("subattachments")
            if isinstance(nested, dict):
                queue.extend(nested.get("data", []))
    return ""


def transform_post(post: dict) -> dict | None:
    permalink = valid_facebook_url(post.get("permalink_url"))
    if not permalink:
        return None
    message = post.get("message")
    if not isinstance(message, str):
        message = ""
    message = message.strip()[:5000]
    return {
        "id": str(post.get("id", ""))[:160],
        "message": message,
        "created_at": str(post.get("created_time", ""))[:64],
        "permalink_url": permalink,
        "image_url": image_from_post(post),
    }


def setup_snapshot() -> dict:
    return {
        "schema_version": 1,
        "status": "setup_required",
        "updated_at": None,
        "page": {"name": PAGE_NAME, "url": PAGE_URL},
        "posts": [],
    }


def fetch_page_posts(page_id: str, token: str) -> dict:
    query = urlencode({
        "fields": "id,message,created_time,permalink_url,full_picture,attachments",
        "limit": str(POST_LIMIT),
        "access_token": token,
    })
    endpoint = f"https://graph.facebook.com/{API_VERSION}/{page_id}/posts?{query}"
    request = Request(endpoint, headers={
        "Accept": "application/json",
        "User-Agent": "TOKI-SATSUEI-SiteFeed/1.0",
    })
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = body.get("error", {}) if isinstance(body, dict) else {}
            code = detail.get("code", "unknown")
            message = str(detail.get("message", "Meta returned an HTTP error"))[:240]
        except (ValueError, UnicodeDecodeError):
            code, message = error.code, "Meta returned an unreadable error response"
        raise RuntimeError(f"Meta Graph API error {code}: {message}") from None
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError(f"Facebook feed request failed: {type(error).__name__}") from None
    if not isinstance(payload, dict):
        raise RuntimeError("Meta returned an unexpected response.")
    if payload.get("error"):
        detail = payload["error"]
        raise RuntimeError(f"Meta Graph API error {detail.get('code', 'unknown')}: {str(detail.get('message', 'Request failed'))[:240]}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("facebook-feed.json"))
    args = parser.parse_args()

    page_id = os.environ.get("META_PAGE_ID", "").strip()
    page_token = os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip()
    existing = read_snapshot(args.output)

    if not page_id or not page_token:
        if not existing:
            write_snapshot(args.output, setup_snapshot())
        print("Facebook feed refresh skipped: configure META_PAGE_ID and META_PAGE_ACCESS_TOKEN as GitHub Actions secrets.")
        return 0

    try:
        response = fetch_page_posts(page_id, page_token)
        raw_posts = response.get("data", [])
        posts = [value for value in (transform_post(item) for item in raw_posts if isinstance(item, dict)) if value]
        snapshot = {
            "schema_version": 1,
            "status": "ready" if posts else "empty",
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "page": {"name": PAGE_NAME, "url": PAGE_URL},
            "posts": posts[:POST_LIMIT],
        }
        write_snapshot(args.output, snapshot)
        print(f"Facebook feed refreshed successfully: {len(snapshot['posts'])} public Page post(s).")
        return 0
    except RuntimeError as error:
        print(f"Facebook feed refresh skipped; preserving the current snapshot. {error}", file=sys.stderr)
        if not existing:
            write_snapshot(args.output, setup_snapshot())
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
