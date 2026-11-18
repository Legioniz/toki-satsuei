# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio. A shared editorial design system keeps the homepage and archive visually consistent across screen sizes and orientations.

- **Live site:** https://legioniz.github.io/toki-satsuei/
- **Design principles:** [DESIGN-PRINCIPLES.md](DESIGN-PRINCIPLES.md) documents the usability, accessibility, and booking-integrity rules behind the site.
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included

- Homepage, services, session guide, FAQs, and inquiry form
- Public booking, payment, rescheduling, privacy, and photo-consent guidelines
- Branded 404 page, `robots.txt`, and XML sitemap for search discovery
- Responsive photo archive with search, category rails, and album viewer
- Cinematic sketchbook art direction: darkroom imagery, contact-sheet galleries, pencil annotations, warm paper textures, and restrained motion
- Shared responsive design system for layout, spacing, color grading, and visual consistency
- Original TOKI SATSUEI brushstroke logo, upload-ready media folders, and automatic archive manifest generator
- Dedicated GitHub Pages workflow and responsive browser regression tests

## Enable GitHub Pages (one-time setup)

In this repository, open **Settings → Pages → Build and deployment** and set **Source** to **GitHub Actions**. GitHub does not allow this workflow connection to create the Pages site automatically for a new repository. After selecting GitHub Actions, rerun the latest workflow from the **Actions** tab. Future pushes to `main` will build and deploy the site automatically.

## Add photos and videos

Upload web-ready JPG, JPEG, PNG, WEBP, AVIF, GIF, MP4, or WEBM files into an album folder under `media-library/`.

Example: `media-library/cosplay/november-convention-2026/portrait-001.jpg`

The build scans those folders and generates `media-library.json` automatically. Do not upload private client-only files or camera RAW files to this public repository.

## Local testing

```bash
python -m pip install -r requirements-test.txt
python -m playwright install --with-deps chromium
python scripts/build-toki-media-library.py
python tests/toki-layout-browser-qa.py
python tests/toki-adaptive-interaction-qa.py
python tests/toki-experience-design-qa.py
python tests/toki-public-pages-qa.py
python tests/toki-booking-browser-qa.py
python tests/toki-availability-calendar-qa.py
python tests/toki-cinematic-design-qa.py
python tests/toki-asset-integration-qa.py
```

## Booking, privacy, and image consent

The public [booking and photo policies](https://legioniz.github.io/toki-satsuei/policies.html) describe how requests are reviewed, how prices and payment terms are agreed, how schedule changes are handled, how files are delivered, and how client photographs may be shared. The inquiry form sends the details you choose to provide to a Supabase Edge Function, which stores them in the private `public.toki_booking_requests` table. Anonymous visitors cannot read or insert directly into that table; the server-side intake is rate-limited and the owner dashboard reads requests under administrator-only Row Level Security. New requests are not reservations, do not hold a date, and do not request payment. Booking administration is handled directly in the Supabase Dashboard. Use the read-only `public.toki_booking_inbox` view to inspect requests and edit the underlying `public.toki_booking_requests` table. No personal-portfolio dashboard is used for TOKI bookings. Client photographs are not added to the public portfolio without permission from the people featured.

The site currently labels its existing gallery images as practice/detail studies. It does not claim to have a finished public cosplay or portrait client portfolio yet.

## Media note

The official TOKI SATSUEI brushstroke logo and the current hero/sample gallery photographs are referenced directly from their original hosted media CDN assets. The logo is used unchanged: the site does not redraw, recolor, or generate a replacement. The website source and upload-ready archive structure remain independent in this repository; those original hosted image files have not been copied into Git because the available GitHub file-transfer connection cannot retrieve the binary media. New archive uploads can be stored directly in this repository under `media-library/`.

## Public monthly availability calendar

The homepage includes a live monthly calendar backed by the separate `toki-calendar` Supabase Edge Function. The private owner queue stores the final `confirmed_date`, `confirmed_start_time`, and `confirmed_end_time` separately from the original preferred and alternate choices. A database check prevents a booking from entering `confirmed` status without a complete, valid time window, and a GiST exclusion constraint rejects overlapping confirmed sessions while allowing multiple bookings on the same date when their windows do not overlap. The public endpoint reads only the confirmed date and start/end times, applies an HMAC-derived per-network quota through the existing atomic quota function, and returns time windows without customer identity or private booking fields. Visitors can select a partially booked date to see its existing time windows and still send an inquiry for another time. The calendar supports a current-month shortcut, keyboard date movement, selected-date preview, explicit inquiry prefill, retry after network errors, automatic one-minute refresh, and Manila-local month rollover. Displayed times use Philippine time. An unmarked time window is not a guaranteed availability promise; all sessions still require written confirmation.

## Runtime integration map

The site is delivered as four static pages with shared behavior and page-specific controllers:

| File | Used by | Responsibility |
| --- | --- | --- |
| `css/*.css` → `toki.css` | All public pages | Source stylesheets live in `css/` and `css/manifest.txt` sets the cascade order. `python3 scripts/build-css.py` bundles and minifies them into the single `toki.css` that every page loads. Edit `css/`, never `toki.css`; CI fails if the bundle is stale. Page-specific sources are scoped with `:where(...)` so they cannot leak onto other pages |
| `library.js` | `library.html` | Archive filters, search, media manifest, and album viewer |
| `media-library.json` + `media-library/` | `library.html` | Generated archive index and uploaded media |

Scripts load with `defer` in dependency order: shared motion first, shared page behavior second, and page-specific behavior last. Controllers are scoped so local declarations cannot collide. The archive manifest separates image, video, and total-media counts; the interface labels the combined count as items instead of treating videos as photographs. The asset-integration QA verifies local links, script ordering, runtime data dependencies, media-manifest totals, stylesheet/script usage, and the standalone Pages package. Empty category folders under `media-library/` are intentional upload shelves, not unused assets.


## Booking form human verification

The booking form uses Cloudflare Turnstile with the `toki_booking` action and the `legioniz.github.io` hostname. The browser sends the short-lived challenge token to the `portfolio-submit` Edge Function; Supabase verifies it with Cloudflare Siteverify before a booking is stored. Missing, invalid, expired, incorrectly scoped, or unverifiable booking tokens are rejected. TOKI booking verification fails closed when its dedicated server-side secret is not configured. The shared personal portfolio keeps its existing `TURNSTILE_SECRET_KEY` for inquiry and comment challenges.

### One-time owner setup

1. Create a Cloudflare Turnstile widget restricted to `legioniz.github.io`.
2. Keep the site key in the public form markup in `index.html`; it is designed to be public.
3. In Supabase **Edge Functions → Secrets**, add `TOKI_TURNSTILE_SECRET_KEY` with the secret that matches the TOKI sitekey. Do not overwrite the existing `TURNSTILE_SECRET_KEY`; it is reserved for the personal portfolio's inquiry/comment widget.
4. After the new secret is saved, deploy the updated `portfolio-submit` Edge Function.
5. Live CI requires missing-token rejection by default; no additional GitHub variable is needed.

## Private booking email notifications

Supabase is the sole source of truth for TOKI booking records. New inquiries are written to the private `public.toki_booking_requests` table by the `portfolio-submit` Edge Function. Booking status, confirmation dates, and exact confirmed start/end times are managed in Supabase. There is no Google Sheets synchronization or external booking spreadsheet.

The existing optional Make.com integration is for administrative email notification only. After a booking has been saved, the Edge Function can send its details to a private Make Custom Webhook, which may send an alert through the owner's connected Gmail account. A Make or Gmail failure does not roll back a saved booking and does not alter the booking status.

### One-time owner setup

1. In Make, create a scenario with **Webhooks → Custom webhook**.
2. Add **Gmail → Send an Email**, connect the owner's Google account, and map the incoming fields from the webhook's `booking` object.
3. Keep the scenario private. Enable API Key authentication on the webhook when available and configure the matching key in the request header.
4. In Supabase **Edge Functions → Secrets**, configure `TOKI_EMAIL_WEBHOOK_URL` and, when API Key authentication is enabled, `TOKI_EMAIL_WEBHOOK_API_KEY`.
5. Run a test from Make and verify that the notification arrives. Separately verify that the booking record appears in Supabase.

Never put webhook URLs, API keys, Supabase secret/service-role keys, or Turnstile secret keys in website JavaScript, a public repository, screenshots, or public documents. Keep these values in Supabase Edge Function secrets. The browser-side Supabase publishable key is intentionally public and is protected by the database's Row Level Security policies.

Make's default webhook response is HTTP 200 with plain-text `Accepted`. That means the notification was queued, not that Gmail delivered the email. Check the Make scenario execution history when diagnosing notification failures. Supabase remains the authoritative booking store.

The source of the intake function is tracked at `supabase/functions/portfolio-submit/index.ts`. It is shared with the main portfolio backend; the TOKI email-notification call runs only for `kind: "toki_booking"` requests.
