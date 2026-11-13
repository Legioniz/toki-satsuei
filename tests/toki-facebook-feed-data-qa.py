#!/usr/bin/env python3
"""Structural validation for TOKI SATSUEI curated post collections."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/"facebook-posts.json").read_text(encoding="utf-8"))
ALLOWED={"cosplay","events","announcements","behind-the-scenes","community","other"}
def main():
    assert DATA.get("schema_version")==2
    assert isinstance(DATA.get("posts"),list) and len(DATA["posts"])<=12
    seen=set()
    for p in DATA["posts"]:
        assert isinstance(p,dict) and p.get("url","").startswith("https://www.facebook.com/")
        assert p["url"] not in seen
        seen.add(p["url"])
        assert p.get("category","other") in ALLOWED
        assert isinstance(p.get("label",""),str) and len(p.get("label",""))<=90
        assert isinstance(p.get("featured",False),bool)
    print("PASS TOKI SATSUEI feed data QA: v2 schema, unique Facebook URLs, categories, labels, and featured flags.")
if __name__=="__main__":main()
