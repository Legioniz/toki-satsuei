# Security and privacy

TOKI booking records belong in the private Supabase project. The Supabase database is the source of truth for inquiries, review status, confirmed dates, and exact confirmed time windows.

## Keep credentials out of source control

Never commit or publish:

- Supabase secret keys, legacy service-role keys, or JWTs.
- Make webhook URLs or Make API keys.
- Cloudflare Turnstile secret keys.
- Database passwords, private keys, OAuth client secrets, or service-account JSON files.
- Local `.env` files or exported credential bundles.

Store server-side values in Supabase Edge Function Secrets. Do not expose them through browser JavaScript, HTML, screenshots, issue reports, or public documents.

The Supabase project URL and `sb_publishable_...` key in the static website are public client configuration, not administrative credentials. They do not bypass Row Level Security. Never replace them with a secret or service-role key.

## Booking data

- Keep client names, contact details, locations, notes, and booking schedules in the private `public.toki_booking_requests` table.
- Use the authenticated, read-only `public.toki_booking_inbox` view to inspect requests.
- Edit the base booking table only as an authorised administrator.
- Do not put client records in this public repository, public spreadsheets, test fixtures, or screenshots.
- Public availability may show confirmed time windows only; it must not reveal client names, contact details, or private notes.
- No Google Sheets booking synchronization is configured. The optional Make integration is only for administrative email notifications; Supabase remains the record of truth.

## Deployment checks

The GitHub Actions workflow runs a static security check for secret patterns, credential files, and personal contact details in public runtime files. This is a guardrail, not a substitute for rotating any credential that may already have been exposed.

If a secret is ever committed, remove the exposed value from the current source, rotate/revoke it at the issuing service immediately, inspect its use, and review Git history. Deleting a value from the latest commit does not invalidate the credential or remove it from previous commits.


## Automated security and dependency scanning

The single GitHub Actions verification workflow performs the following checks before deployment:

- GitHub's repository-level CodeQL default setup analyzes JavaScript/TypeScript, Python, and GitHub Actions workflow code and publishes results to GitHub code scanning. It runs as a GitHub-managed dynamic workflow, separate from the single tracked deployment workflow.
- Gitleaks scans the complete Git history and checked-out working tree for credential patterns (`fetch-depth: 0`). Its only explicit allowlist is the `sb_publishable_...` key format, which Supabase documents as safe for frontend use when RLS and least-privilege policies are correctly configured. Secret keys and generic API-key findings are not allowlisted. The scanner binary is version-pinned and its release archive is SHA-256 verified before execution; findings are redacted in logs.
- `pip-audit` checks the Python test dependencies in `requirements-test.txt` against known vulnerability advisories.
- Dependabot checks the Python dependency manifest and GitHub Actions references weekly and can propose update pull requests.

These checks are additional guardrails, not proof that the application is vulnerability-free. The Gitleaks CI step now scans the repository's available Git history as well as the checked-out tree. If a credential is detected in any historical commit, treat it as exposed and rotate it immediately; deleting it from later commits does not invalidate it. If a credential may have appeared in any earlier commit, rotate it immediately and inspect the repository history.

## Hosting response headers

The current production site is deployed on GitHub Pages. GitHub Pages does not apply `_headers` as HTTP response headers, so HSTS, response CSP, X-Frame-Options, Permissions-Policy, and custom Cache-Control values are not active at the current github.io origin. The repository now contains a Cloudflare Pages-compatible _headers policy, consistent CSP meta fallbacks, content-hash asset URLs, and a post-deployment response verifier. The meta fallback cannot enforce HSTS or frame-ancestors and cannot set response cache policy. Treat response-level controls as pending until the site is served by a header-capable host and the strict live verifier passes.


## TOKI API and traffic enforcement

All listed quotas are server-enforced fixed windows of 10 minutes. Quota-service failures fail closed.

| Operation | Limit per 10 minutes | Additional constraints |
|---|---:|---|
| Booking intake per network bucket | 4 | Turnstile; JSON body <= 12,000 bytes |
| Shared Turnstile verification attempts per network | 20 | Separate ceiling; failed CAPTCHA attempts do not consume normal submission quotas |
| Booking intake per normalized contact | 2 | HMAC-derived bucket |
| Public availability calendar per network bucket | 30 | GET only; confirmed date/time projection |
| Client gallery global | 120 | Shared abuse ceiling |
| Client gallery per access token | 10 | 256-bit random token; SHA-256 hash stored |
| General inquiry | 4 | Turnstile; bounded fields |
| Comment submission | 6 | Turnstile; moderation pending |
| Consented page-view event | 60 | Bounded path and UUID session ID |

Booking caps: 12 participants, 50 additional photos, 120 additional minutes in 15-minute increments, and 2,000 note characters. Gallery selections: 50 unique IDs, each <= 128 characters. Calendar rate-limit responses advertise 600 seconds, matching the database fixed window.

## Non-negotiable application rules

1. Never place Supabase secret/service-role keys, webhook credentials, Turnstile secrets, or database passwords in browser assets or Git history.
2. Browser code may use only the Supabase publishable key. Privileged access stays in Edge Functions or tightly scoped private database functions.
3. Anonymous REST access to booking rows remains denied. Public availability is a field-minimized projection only.
4. Public write APIs enforce method, origin, content type, body-size limits, schema validation, abuse quotas, and human verification where applicable. CORS is not authentication.
5. Quota checks fail closed. Never expose an RPC that lets anonymous callers allocate arbitrary quota buckets or alter limits.
6. Network rate limits must use only the Cloudflare-overwritten `cf-connecting-ip` header. Never trust caller-supplied `X-Forwarded-For` or `X-Real-IP`; use a shared fail-closed bucket if the trusted header is unavailable.
7. Client-gallery quota rows and the shared gallery quota must be charged only after an active, unexpired delivery token has been found. Random or expired tokens must not allocate quota rows or consume the shared quota.
8. Delivery tokens remain cryptographically random; only hashes are persisted; expiry and revocation are checked on every use; global and per-token traffic are limited.
9. SECURITY DEFINER functions require an empty or explicitly safe search_path, qualified object names, narrow EXECUTE grants, input validation, and authorization review.
10. Schema changes are migration-tracked, scoped to TOKI-owned objects, and followed by Supabase advisors and live authorization tests.
11. Do not change shared Supabase roles, global Auth settings, unrelated tables, or unrelated functions without impact review.
12. Production deployment must pass the single repository workflow, including history/secret scans, dependency audit, static QA, browser QA, and live API boundary checks.
13. Production deployment is restricted to `refs/heads/main`, including manually dispatched workflow runs. A successful verification run from another branch must never deploy the Pages production environment.
14. Preserve Git history. Never force-push or rewrite history routinely. If a secret enters history, rotate it immediately; history rewriting is secondary and coordinated.
15. Configure GitHub rulesets outside code: require PRs and successful verification, block force pushes and branch deletion, require conversation resolution, and restrict bypass. The connected GitHub integration cannot administer these settings.

These rules reduce risk; they do not make a site invulnerable. The current GitHub Pages origin still cannot apply _headers. The post-deployment probe reports those missing controls, and must be run with TOKI_REQUIRE_SECURITY_HEADERS=1 against the replacement origin before the migration is treated as complete.


## Delivery-key storage and admin-session rules

Delivery keys are 256-bit cryptographically random values. Only SHA-256 hashes are stored in the database; raw keys are displayed only when generated and cannot be recovered. Keys expire 30 days after issuance and can be revoked by clearing the private delivery URL. Gallery RPC entry points run as invoker and delegate to narrowly scoped functions in the non-exposed `private` schema. The internal quota RPC is not executable by browser roles.

The admin dashboard persists only its short-lived access token, not a refresh token. It revokes the remote Supabase Auth session on logout and automatically logs out after 20 minutes of inactivity. The dashboard's booking status controls are aligned with the database's allowed values.

## Remaining owner-only security settings

Supabase Auth's leaked-password protection is currently disabled. Enable it in Supabase Dashboard → Authentication → Settings → Password Security, then review Auth rate limits and session lifetime. The connected Supabase tools do not expose these project-level Auth settings.

No GitHub branch ruleset is currently configured. The GitHub integration used here can inspect rulesets but cannot create or edit them. Apply the repository ruleset described in `.github/SECURITY-RULESET.md` from GitHub Settings → Rules → Rulesets.

The site remains on GitHub Pages until a hosting cutover is completed. The _headers file is prepared for Cloudflare Pages, but remains inactive on the current origin. Do not describe response-level CSP, HSTS, frame restrictions, or immutable Cache-Control as live protections until the strict live-site check confirms them.



## Deliberate public client-gallery RPC exception

The public `toki_get_client_gallery` and `toki_submit_client_selection` RPC wrappers are intentionally callable by `anon` and `authenticated` clients and run as `SECURITY DEFINER`. They are bearer-token APIs, not general booking-table access: each call is delegated to a function in the non-exposed `private` schema, which validates the 256-bit delivery key, hashes it before lookup, checks delivery state and expiry, enforces per-token/global quotas, and returns or changes only the gallery fields. Direct EXECUTE on the private implementation functions is revoked from `PUBLIC`, `anon`, and `authenticated`. Keep the `private` schema out of the PostgREST exposed-schema list. Supabase advisor warnings for these two public wrappers are expected and must be re-reviewed whenever their implementation changes.

## Sensitive-data-safe operational logging

The booking Edge Function must never write a PostgREST error response body or submitted booking record to logs. Database failures may log only the internal table name, HTTP status, and a validated five-character database error code. The Make notification request rejects redirects so its custom API-key header cannot be forwarded to a redirect destination. Do not add request-body, token, contact, or credential logging to diagnose production issues.


Production deployment is restricted to `refs/heads/main`, including manually dispatched workflow runs. A successful verification run from another branch must never deploy the Pages production environment.
