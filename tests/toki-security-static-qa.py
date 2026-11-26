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
    "index.html", "booking.html", "library.html", "policies.html", "404.html", "client-gallery.html",
    "site.js", "availability.js", "library.js", "client-gallery.js",
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

# Platform migration must enforce the live admin allowlist for journal writes and
# must never disclose expired/unready delivery folders through public token RPCs.
platform_migration = ROOT / "supabase" / "migrations" / "20261123120000_toki_v2_core_platform.sql"
if not platform_migration.exists():
    problems.append("platform migration: required file is missing")
else:
    migration = platform_migration.read_text(encoding="utf-8")
    for required in (
        "CREATE OR REPLACE FUNCTION private.is_portfolio_admin()",
        "SET search_path = ''",
        "USING ((SELECT private.is_portfolio_admin()))",
        "WITH CHECK ((SELECT private.is_portfolio_admin()))",
        "delivery_status IN ('ready', 'delivered')",
        "delivery_folder_url IS NOT NULL",
        "jsonb_array_length(p_selections) > 50",
        "SET search_path = ''",
    ):
        if required not in migration:
            problems.append(f"platform migration: missing security control: {required}")
    if 'USING (true)' in migration or 'WITH CHECK (true)' in migration:
        problems.append("platform migration: unrestricted authenticated journal write policy detected")

client_gallery = ROOT / "client-gallery.js"
if client_gallery.exists():
    gallery_source = client_gallery.read_text(encoding="utf-8")
    if "DEFAULT_PHOTOS" in gallery_source:
        problems.append("client-gallery.js: fabricated fallback photos must not appear as client deliveries")
    if "new URLSearchParams(window.location.search)" in gallery_source:
        problems.append("client-gallery.js: bearer access keys must not be accepted from query strings")

admin_source = (ROOT / "admin.js").read_text(encoding="utf-8")
if "Math.random().toString(36)" in admin_source:
    problems.append("admin.js: delivery access keys must use a cryptographically secure random generator")
if "crypto.getRandomValues" not in admin_source:
    problems.append("admin.js: secure delivery-key generator is missing")


security_migration = ROOT / "supabase" / "migrations" / "20261126005625_toki_security_hardening.sql"
if not security_migration.exists():
    problems.append("TOKI security migration: required file is missing")
else:
    sql = security_migration.read_text(encoding="utf-8")
    for marker in ("SET search_path = ''", "toki_booking_contact", "REVOKE ALL ON FUNCTION public.consume_portfolio_quota", "FORCE ROW LEVEL SECURITY", "AFTER INSERT OR UPDATE OR DELETE", "Changed fields:"):
        if marker not in sql:
            problems.append(f"TOKI security migration: missing control: {marker}")

delivery_migration = ROOT / "supabase" / "migrations" / "20261126010019_toki_delivery_token_hardening.sql"
if not delivery_migration.exists():
    problems.append("TOKI delivery migration: required file is missing")
else:
    sql = delivery_migration.read_text(encoding="utf-8")
    for marker in ("delivery_token_hash", "extensions.digest(p_token,'sha256')", "toki_gallery_global", "toki_gallery_token", "delivery_expires_at"):
        if marker not in sql:
            problems.append(f"TOKI delivery migration: missing control: {marker}")
    if "delivery_token text" in sql or "delivery_token =" in sql:
        problems.append("TOKI delivery migration: raw access-token storage detected")

rpc_isolation = ROOT / "supabase" / "migrations" / "20261126010625_toki_gallery_rpc_privilege_isolation.sql"
if not rpc_isolation.exists():
    problems.append("TOKI gallery RPC isolation migration: required file is missing")
else:
    sql = rpc_isolation.read_text(encoding="utf-8")
    for marker in ("private.toki_get_client_gallery", "private.toki_submit_client_selection", "SECURITY DEFINER", "SECURITY INVOKER", "SET search_path = ''"):
        if marker not in sql:
            problems.append(f"TOKI gallery RPC isolation migration: missing control: {marker}")

audit_migration = ROOT / "supabase" / "migrations" / "20261126012559_toki_admin_activity_append_only.sql"
if not audit_migration.exists():
    problems.append("TOKI audit immutability migration: required file is missing")
else:
    sql = audit_migration.read_text(encoding="utf-8")
    for marker in ("FORCE ROW LEVEL SECURITY", "FROM PUBLIC, anon, authenticated, service_role", "admin_activity_append_only", "append-only"):
        if marker not in sql:
            problems.append(f"TOKI audit immutability migration: missing control: {marker}")

booking_function = (ROOT / "supabase" / "functions" / "portfolio-submit" / "index.ts").read_text(encoding="utf-8")
if "consumeQuota(contactBucket, 'toki_booking_contact', 2)" not in booking_function:
    problems.append("Booking intake: per-contact booking quota is missing")
if "Content-Type must be application/json" not in booking_function:
    problems.append("Booking intake: strict JSON content-type enforcement is missing")

admin_source = (ROOT / "admin.js").read_text(encoding="utf-8")
if "delivery_token:" in admin_source or "b.delivery_token ||" in admin_source:
    problems.append("admin.js: raw delivery token must never be read from or written to the database")
if "delivery_token_hash" not in admin_source or "sha256Hex" not in admin_source:
    problems.append("admin.js: hash-only delivery token storage is missing")
if "ADMIN_IDLE_TIMEOUT_MS" not in admin_source or "/auth/v1/logout" not in admin_source:
    problems.append("admin.js: admin idle logout and remote session revocation are missing")
if "under_review" in admin_source or "awaiting_reservation_fee" in admin_source:
    problems.append("admin.js: booking status values do not match the database")

# Keep the automated security scanning configuration from silently disappearing.
workflow = ROOT / ".github" / "workflows" / "deploy.yml"
if not workflow.exists():
    problems.append(".github/workflows/deploy.yml: required security workflow is missing")
else:
    workflow_text = workflow.read_text(encoding="utf-8")
    for label, marker in (
        ("Gitleaks full-history scan", "gitleaks git --redact --verbose"),
        ("Python dependency audit", "pip-audit -r requirements-test.txt"),
    ):
        if marker not in workflow_text:
            problems.append(f"deploy workflow: missing {label}")

dependabot = ROOT / ".github" / "dependabot.yml"
if not dependabot.exists():
    problems.append(".github/dependabot.yml: dependency update configuration is missing")
else:
    dependabot_text = dependabot.read_text(encoding="utf-8")
    for ecosystem in ('package-ecosystem: "pip"', 'package-ecosystem: "github-actions"'):
        if ecosystem not in dependabot_text:
            problems.append(f"Dependabot configuration: missing {ecosystem}")


gitleaks_config = ROOT / ".gitleaks.toml"
if not gitleaks_config.exists():
    problems.append(".gitleaks.toml: narrowly scoped public-key allowlist is missing")
else:
    gitleaks_text = gitleaks_config.read_text(encoding="utf-8")
    if "sb_publishable_[A-Za-z0-9_-]{16,}" not in gitleaks_text:
        problems.append(".gitleaks.toml: expected Supabase publishable-key allowlist is missing")
    if "sb_secret_" in gitleaks_text or "generic-api-key" in gitleaks_text:
        problems.append(".gitleaks.toml: secret or generic API-key rules must not be allowlisted")

if problems:
    print("FAIL TOKI static security audit:")
    for problem in problems:
        print(f"- {problem}")
    sys.exit(1)

print("PASS TOKI static security audit: no committed secret patterns, private credential files, or personal contact details in public runtime source.")
