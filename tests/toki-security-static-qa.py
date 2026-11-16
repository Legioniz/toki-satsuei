#!/usr/bin/env python3
"""Static checks that prevent secrets and personal data entering the public TOKI source."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "node_modules"}
TEXT_SUFFIXES = {
    ".html", ".js", ".css", ".json", ".md", ".py", ".ts", ".yml", ".yaml",
    ".txt", ".xml", ".toml", ".sql", ".sh"
}

SECRET_PATTERNS = [
    ("Supabase secret key", re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}\b")),
    ("JWT-like token", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("GitHub access token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Stripe live secret", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Hard-coded Make webhook URL", re.compile(r"https?://hook\.[A-Za-z0-9.-]+/[A-Za-z0-9_-]{12,}")),
]

# Contact details must not be embedded in the browser-facing website or public Edge Function source.
PUBLIC_SOURCE_FILES = [
    "index.html", "library.html", "policies.html", "404.html",
    "site.js", "availability.js", "library.js",
    "supabase/functions/portfolio-submit/index.ts",
    "supabase/functions/toki-calendar/index.ts",
]
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PH_MOBILE_PATTERN = re.compile(r"(?<!\d)(?:\+?63|0)9\d{9}(?!\d)")
OWNER_NAME_PATTERN = re.compile(r"\bKing\s+Art(?:\s+D\.?)?\s+Pacumberto\b", re.IGNORECASE)

problems = []

for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
        continue
    rel = path.relative_to(ROOT)
    name = path.name.lower()

    # Local secrets must stay out of the repository, even if they are not referenced by code.
    if name.startswith(".env") and name not in {".env.example", ".env.sample"}:
        problems.append(f"{rel}: local environment file must not be committed")
        continue
    if name in {"credentials.json", "token.json"} or "service-account" in name or name.endswith((".pem", ".p12", ".pfx")):
        problems.append(f"{rel}: credential or private-key file must not be committed")
        continue
    if path.suffix.lower() not in TEXT_SUFFIXES:
        continue

    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(content):
            problems.append(f"{rel}: possible {label} detected")

for relative in PUBLIC_SOURCE_FILES:
    path = ROOT / relative
    if not path.exists():
        problems.append(f"{relative}: required public source file is missing")
        continue
    content = path.read_text(encoding="utf-8")
    for label, pattern in (
        ("email address", EMAIL_PATTERN),
        ("Philippine mobile number", PH_MOBILE_PATTERN),
        ("owner legal name", OWNER_NAME_PATTERN),
    ):
        if pattern.search(content):
            problems.append(f"{relative}: possible personal {label} embedded in public source")

if problems:
    print("FAIL TOKI static security audit:")
    for problem in problems:
        print(f"- {problem}")
    sys.exit(1)

print("PASS TOKI static security audit: no committed secret patterns, private credential files, or personal contact details in public runtime source.")
