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
