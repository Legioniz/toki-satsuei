#!/usr/bin/env python3
"""Unit checks for the Meta Graph API feed snapshot transformer."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fetch_facebook_feed", ROOT / "scripts" / "fetch_facebook_feed.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def main() -> None:
    source = {
        "id": "123_456",
        "message": "A TOKI SATSUEI update",
        "created_time": "2026-11-14T02:00:00+0000",
        "permalink_url": "https://www.facebook.com/tokisatsuiephotography/posts/456",
        "full_picture": "https://scontent.xx.fbcdn.net/photo.jpg",
    }
    post = MODULE.transform_post(source)
    assert post is not None
    assert post["id"] == "123_456"
    assert post["message"] == "A TOKI SATSUEI update"
    assert post["image_url"].startswith("https://")
    assert post["permalink_url"].startswith("https://www.facebook.com/")

    assert MODULE.transform_post({**source, "permalink_url": "http://facebook.com/post/1"}) is None
    assert MODULE.transform_post({**source, "permalink_url": "https://example.com/post/1"}) is None
    assert MODULE.transform_post({**source, "message": "<script>alert(1)</script>"})["message"] == "<script>alert(1)</script>"

    nested = {
        "attachments": {"data": [{
            "media": {"image": {"src": "https://scontent.xx.fbcdn.net/nested.jpg"}}
        }]}
    }
    assert MODULE.image_from_post(nested).endswith("/nested.jpg")
    print("PASS TOKI SATSUEI Facebook feed data QA: Page URL validation, safe plain-text fields, and attachment image extraction.")


if __name__ == "__main__":
    main()
