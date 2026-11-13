#!/usr/bin/env python3
"""Structural validation for TOKI SATSUEI curated post collections."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/"facebook-posts.json").read_text(encoding="utf-8"))
ALLOWED={"cosplay","events","announcements","behind-the-scenes","community","other"}
FACEBOOK_HOSTS={"facebook.com","www.facebook.com","m.facebook.com","web.facebook.com"}

def main():
    assert DATA.get("schema_version")==2
    assert isinstance(DATA.get("posts"),list) and len(DATA["posts"])<=12
    seen=set()
    for post in DATA["posts"]:
        assert isinstance(post,dict)
        url=post.get("url","")
        parsed=urlparse(url)
        assert parsed.scheme=="https" and parsed.hostname in FACEBOOK_HOSTS, f"Unsupported Facebook URL: {url!r}"
        assert any(segment in parsed.path for segment in ("/posts/","/permalink/","/videos/","/reel/","/photo/","/watch","/share/p/","/share/r/")), f"Unsupported Facebook post path: {url!r}"
        assert url not in seen
        seen.add(url)
        assert post.get("category","other") in ALLOWED
        assert isinstance(post.get("label",""),str) and len(post.get("label",""))<=90
        assert isinstance(post.get("featured",False),bool)
    print("PASS TOKI SATSUEI feed data QA: v2 schema, Facebook hosts and post paths, unique URLs, categories, labels, and featured flags.")

if __name__=="__main__":
    main()
