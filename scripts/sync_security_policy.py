#!/usr/bin/env python3
"""Synchronize and validate TOKI security headers and CSP across _headers, worker.mjs, and HTML meta."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "security-policy.json"
HEADERS_PATH = ROOT / "_headers"
WORKER_PATH = ROOT / "worker.mjs"

WORKER_BLOCK_RE = re.compile(
    r"// BEGIN_SECURITY_POLICY\n.*?// END_SECURITY_POLICY",
    re.DOTALL,
)


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_csp(csp: dict[str, list[str]], *, include_frame_ancestors: bool = True) -> str:
    parts: list[str] = []
    for directive, sources in csp.items():
        if not include_frame_ancestors and directive == "frame-ancestors":
            continue
        if sources:
            parts.append(f"{directive} {' '.join(sources)}")
        else:
            parts.append(directive)
    return "; ".join(parts)


def build_csp_meta(path: Path = POLICY_PATH) -> str:
    """Return the HTML <meta http-equiv='Content-Security-Policy'> string."""
    return format_csp(load_policy(path)["csp"], include_frame_ancestors=False)


def render_pages_headers(policy: dict) -> str:
    lines = [
        "/*",
        f"  Strict-Transport-Security: {policy['hsts']}",
    ]
    for name, value in policy["security_headers"].items():
        lines.append(f"  {name}: {value}")
    lines.append(f"  Content-Security-Policy: {format_csp(policy['csp'], include_frame_ancestors=True)}")
    lines.append(f"  Cache-Control: {policy['cache']['default']}")

    for route in policy["cache"]["no_store_routes"]:
        lines.extend(["", route, "  ! Cache-Control", "  Cache-Control: no-store"])

    immutable = policy["cache"]["immutable_header"]
    for pattern in policy["cache"]["immutable_paths"]:
        lines.extend(["", pattern, "  ! Cache-Control", f"  Cache-Control: {immutable}"])

    return "\n".join(lines) + "\n"


def render_worker_block(policy: dict) -> str:
    headers_obj = {
        "Content-Security-Policy": format_csp(policy["csp"], include_frame_ancestors=True),
        **policy["security_headers"],
    }
    headers_json = json.dumps(headers_obj, indent=2)
    no_store_json = json.dumps(policy["cache"]["no_store_routes"], indent=2)
    hsts_json = json.dumps(policy["hsts"])
    default_cache_json = json.dumps(policy["cache"]["default"])
    immutable_cache_json = json.dumps(policy["cache"]["immutable_header"])

    return (
        "// BEGIN_SECURITY_POLICY\n"
        f"const SECURITY_HEADERS = {headers_json};\n"
        f"const HSTS_HEADER = {hsts_json};\n"
        f"const NO_STORE_PATHS = new Set({no_store_json});\n"
        f"const DEFAULT_CACHE_CONTROL = {default_cache_json};\n"
        f"const IMMUTABLE_CACHE_CONTROL = {immutable_cache_json};\n"
        "// END_SECURITY_POLICY"
    )


def sync_all(*, check: bool = False) -> list[str]:
    policy = load_policy()
    expected_headers = render_pages_headers(policy)
    expected_worker_block = render_worker_block(policy)

    worker_text = WORKER_PATH.read_text(encoding="utf-8")
    if not WORKER_BLOCK_RE.search(worker_text):
        raise RuntimeError("worker.mjs is missing // BEGIN_SECURITY_POLICY ... // END_SECURITY_POLICY markers")
    expected_worker = WORKER_BLOCK_RE.sub(lambda _: expected_worker_block, worker_text, count=1)

    stale: list[str] = []
    current_headers = HEADERS_PATH.read_text(encoding="utf-8") if HEADERS_PATH.exists() else ""
    if current_headers != expected_headers:
        stale.append("_headers")
        if not check:
            HEADERS_PATH.write_text(expected_headers, encoding="utf-8", newline="\n")

    if worker_text != expected_worker:
        stale.append("worker.mjs")
        if not check:
            WORKER_PATH.write_text(expected_worker, encoding="utf-8", newline="\n")

    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync or check TOKI security policy outputs.")
    parser.add_argument("--check", action="store_true", help="Fail if _headers or worker.mjs is out of sync.")
    args = parser.parse_args()

    stale = sync_all(check=args.check)
    if args.check:
        if stale:
            print("FAIL security policy out of sync: " + ", ".join(stale) + ". Run python scripts/sync_security_policy.py.")
            return 1
        print("PASS security policy sync: _headers, worker.mjs, and security-policy.json match.")
        return 0

    if stale:
        print("Updated security policy targets: " + ", ".join(stale))
    else:
        print("Security policy targets already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
