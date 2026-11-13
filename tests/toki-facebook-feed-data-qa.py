#!/usr/bin/env python3
"""Structural checks for the curated Facebook post configuration."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"facebook-posts.json").read_text(encoding="utf-8"))
def main():
    assert CONFIG.get("schema_version")==1
    assert isinstance(CONFIG.get("posts"),list)
    assert len(CONFIG["posts"])<=12
    for post in CONFIG["posts"]:
        assert isinstance(post,dict)
        assert post["url"].startswith("https://www.facebook.com/")
    print("PASS TOKI SATSUEI curated feed data QA: valid schema, bounded post count, and Facebook-only URLs.")
if __name__=="__main__":main()
