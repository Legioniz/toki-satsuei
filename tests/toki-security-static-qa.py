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
if "const errorPayload = await result.json().catch(() => null)" not in booking_function:
    problems.append("Booking intake: database error response must be parsed without logging submitted values")
if "console.error('Portfolio submission failed:', { requestId, errorType: error instanceof Error ? error.name : 'unknown' })" not in booking_function:
    problems.append("Booking intake: outer error logging must not serialize exception details")
if "consumeQuota(bucket, 'portfolio_turnstile_verify', 20)" not in booking_function:
    problems.append("Booking intake: dedicated CAPTCHA verification abuse quota is missing")
if "function trustedClientAddress(request: Request): string | null" not in booking_function:
    problems.append("Booking intake: trusted client IP helper must expose its nullable return type")
if "return null;" not in booking_function or "if (!forwarded)" not in booking_function:
    problems.append("Booking intake: missing trusted client IP must fail closed")
if "console.error('Insert failed', { table, status: result.status, databaseCode })" not in booking_function:
    problems.append("Booking intake: database logs must contain only table, HTTP status, and safe SQLSTATE")
if "redirect: 'error'" not in booking_function:
    problems.append("Booking notification: webhook redirects must be rejected to protect its API key")
if "&& TOKI_TURNSTILE_SECRET)" not in booking_function:
    problems.append("Booking service health probe: required TOKI Turnstile secret must be included in readiness")

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

    for marker in (
        "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
        "cloudflare/wrangler-action@v4.1.3",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "pages deploy dist --project-name=toki-satsuei --branch=main",
        "TOKI_REQUIRE_SECURITY_HEADERS: '1'",
        "https://toki-satsuei.pages.dev/",
    ):
        if marker not in workflow_text:
            problems.append(f"deploy workflow: missing strict Cloudflare Pages deployment control: {marker}")
    if "actions/deploy-pages@" in workflow_text or "actions/upload-pages-artifact@" in workflow_text:
        problems.append("deploy workflow: GitHub Pages deployment actions must be removed so _headers is enforced by Cloudflare Pages")

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



quota_dos_migration = ROOT / "supabase" / "migrations" / "20261126025446_toki_gallery_quota_dos_hardening.sql"
if not quota_dos_migration.exists():
    problems.append("TOKI gallery quota migration: required file is missing")
else:
    sql = quota_dos_migration.read_text(encoding="utf-8")
    for marker in ("v_result IS NULL", "v_booking_id IS NULL", "toki_gallery_token", "toki_gallery_global"):
        if marker not in sql:
            problems.append(f"TOKI gallery quota migration: missing control: {marker}")
    if sql.index("INTO v_result") > sql.index("toki_gallery_global"):
        problems.append("TOKI gallery quota migration: global quota must be charged only after an active token lookup")


private_rpc_migration = ROOT / "supabase" / "migrations" / "20261126032900_toki_gallery_private_execute_lockdown.sql"
if not private_rpc_migration.exists():
    problems.append("TOKI gallery private RPC migration: required file is missing")
else:
    sql = private_rpc_migration.read_text(encoding="utf-8")
    for marker in ("SECURITY DEFINER", "FROM PUBLIC, anon, authenticated", "TO anon, authenticated"):
        if marker not in sql:
            problems.append(f"TOKI gallery private RPC migration: missing control: {marker}")


turnstile_quota_migration = ROOT / "supabase" / "migrations" / "20261126033301_toki_turnstile_verification_quota_ceiling.sql"
if not turnstile_quota_migration.exists():
    problems.append("TOKI Turnstile quota migration: required file is missing")
else:
    sql = turnstile_quota_migration.read_text(encoding="utf-8")
    if "WHEN 'portfolio_turnstile_verify' THEN 20" not in sql:
        problems.append("TOKI Turnstile quota migration: dedicated verification ceiling is missing")
    if "p_limit > v_scope_ceiling" not in sql:
        problems.append("TOKI Turnstile quota migration: requested quota ceiling validation is missing")


turnstile_scope_constraint_migration = ROOT / "supabase" / "migrations" / "20261126033336_toki_turnstile_scope_allowlist.sql"
if not turnstile_scope_constraint_migration.exists():
    problems.append("TOKI Turnstile scope constraint migration: required file is missing")
else:
    sql = turnstile_scope_constraint_migration.read_text(encoding="utf-8")
    if "portfolio_turnstile_verify" not in sql or "submission_rate_limits_scope_allowlist_check" not in sql:
        problems.append("TOKI Turnstile scope constraint migration: table scope allowlist is missing the verification scope")


gallery_selection_guard_migration = ROOT / "supabase" / "migrations" / "20261126033603_toki_gallery_selection_type_guard.sql"
if not gallery_selection_guard_migration.exists():
    problems.append("TOKI gallery selection JSON guard migration: required file is missing")
else:
    sql = gallery_selection_guard_migration.read_text(encoding="utf-8")
    expected = (
        "IF p_selections IS NULL THEN",
        "jsonb_typeof(p_selections) IS DISTINCT FROM 'array'",
        "IF pg_catalog.jsonb_array_length(p_selections) > 50 THEN",
        "SET search_path = ''",
    )
    for marker in expected:
        if marker not in sql:
            problems.append(f"TOKI gallery selection JSON guard migration: missing {marker}")


# Hosting and cache controls must remain wired to the production build.
headers_path = ROOT / "_headers"
if not headers_path.exists():
    problems.append("_headers: response security policy is missing")
else:
    headers_text = headers_path.read_text(encoding="utf-8")
    for marker in (
        "Strict-Transport-Security: max-age=31536000",
        "X-Frame-Options: SAMEORIGIN",
        "X-Content-Type-Options: nosniff",
        "Referrer-Policy: strict-origin-when-cross-origin",
        "Permissions-Policy: camera=(), microphone=(), geolocation=()",
        "frame-ancestors 'self'",
        "Cache-Control: no-store",
        "Cache-Control: public, max-age=31536000, immutable",
        "must-revalidate",
    ):
        if marker not in headers_text:
            problems.append(f"_headers: required response/cache rule is missing: {marker}")

fingerprint_builder = ROOT / "scripts" / "fingerprint_assets.py"
if not fingerprint_builder.exists():
    problems.append("scripts/fingerprint_assets.py: deterministic cache fingerprint builder is missing")
else:
    fingerprint_text = fingerprint_builder.read_text(encoding="utf-8")
    for marker in ("hashlib.sha256", "normalize_csp_fallbacks", "verify_references", "HASH_LENGTH = 32"):
        if marker not in fingerprint_text:
            problems.append(f"asset fingerprint builder: missing control {marker}")

live_probe = ROOT / "tests" / "toki-live-site-security-qa.py"
if not live_probe.exists():
    problems.append("tests/toki-live-site-security-qa.py: live HTTP response verification is missing")
else:
    live_text = live_probe.read_text(encoding="utf-8")
    for marker in (
        "strict-transport-security",
        "content-security-policy",
        "immutable",
        "hashlib.sha256",
        '("404.html", False)',
        '("admin.html", True)',
        '("client-gallery.html", True)',
    ):
        if marker not in live_text:
            problems.append(f"live site security probe: missing check {marker}")

if workflow.exists():
    for marker in (
        "python scripts/fingerprint_assets.py --self-test",
        "python scripts/fingerprint_assets.py dist",
        "python scripts/fingerprint_assets.py dist --verify-only",
        "python tests/toki-live-site-security-qa.py",
        "TOKI_REQUIRE_SECURITY_HEADERS: '1'",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
    ):
        if marker not in workflow_text:
            problems.append(f"deploy workflow: missing runtime security verification: {marker}")

for edge_path in (
    "supabase/functions/portfolio-submit/index.ts",
    "supabase/functions/toki-calendar/index.ts",
):
    edge_source = (ROOT / edge_path).read_text(encoding="utf-8")
    for marker in (
        "PORTFOLIO_ADDITIONAL_ALLOWED_ORIGINS",
        "https://toki-satsuei.pages.dev",
        "function isAllowedOrigin(origin: string | null)",
        "ALLOWED_ORIGINS.has(origin)",
    ):
        if marker not in edge_source:
            problems.append(f"{edge_path}: missing exact Cloudflare Pages origin allowlist control: {marker}")

booking_edge = (ROOT / "supabase/functions/portfolio-submit/index.ts").read_text(encoding="utf-8")
if "payload.hostname === expectedHostname" not in booking_edge or "hostnameForOrigin(origin)" not in booking_edge:
    problems.append("portfolio-submit: Turnstile hostname must be verified against the allowlisted request origin")

if problems:
    print("FAIL TOKI static security audit:")
    for problem in problems:
        print(f"- {problem}")
    sys.exit(1)

print("PASS TOKI static security audit: no committed secret patterns, private credential files, or personal contact details in public runtime source.")
