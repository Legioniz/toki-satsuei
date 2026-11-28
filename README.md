# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio. A shared editorial design system keeps the homepage and archive visually consistent across screen sizes and orientations.

- **Production URL (after first Cloudflare Pages deployment):** https://toki-satsuei.pages.dev/
- **Design principles:** [DESIGN-PRINCIPLES.md](DESIGN-PRINCIPLES.md) documents the usability, accessibility, and booking-integrity rules behind the site.
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included

- Homepage, services, session guide, FAQs, and a dedicated online booking page
- Public booking, payment, rescheduling, privacy, and photo-consent guidelines
- Branded 404 page, `robots.txt`, and XML sitemap for search discovery
- Responsive photo archive with search, category rails, and album viewer
- Cinematic sketchbook art direction: darkroom imagery, contact-sheet galleries, pencil annotations, warm paper textures, and restrained motion
- Shared responsive design system for layout, spacing, color grading, and visual consistency
- Original TOKI SATSUEI brushstroke logo, upload-ready media folders, and automatic archive manifest generator
- Dedicated Cloudflare Pages production deployment and responsive browser regression tests

## Cloudflare Pages production deployment

The production workflow now deploys the already-tested `dist/` artifact to Cloudflare Pages using Wrangler Direct Upload. It creates the `toki-satsuei` Pages project on the first production run, deploys fresh `main` commits only, and no longer uses GitHub Pages deployment actions.

Before the first production deployment, add these two values under GitHub **Settings → Secrets and variables → Actions → Repository secrets**:

1. `CLOUDFLARE_API_TOKEN` — an account-scoped Cloudflare API token with **Cloudflare Pages: Edit/Write** permission.
2. `CLOUDFLARE_ACCOUNT_ID` — the Cloudflare account ID that owns the Pages project.

The workflow publishes to [https://toki-satsuei.pages.dev/](https://toki-satsuei.pages.dev/) by default. An optional repository variable named `TOKI_SITE_URL` can point the live verifier to a configured HTTPS custom domain. Do not set it to a preview URL.

The previous `github.io/toki-satsuei` address is a legacy copy; this workflow no longer deploys to GitHub Pages. Keep it only as a temporary fallback until the Cloudflare Pages site is verified and the public links have been updated.

Cloudflare Workers Builds remains enabled for main-branch production Worker builds. Its optional pull-request preview builds are disabled because this repository’s production website is packaged and deployed through the Cloudflare Pages workflow above; the Worker preview command requires a separate Wrangler `previews` configuration that this static Pages repository does not use. This does not disable production Worker builds or Cloudflare Pages deployments. Main-branch Worker builds use `wrangler.worker.jsonc` and `scripts/build_static_site.py --target worker` to create a dedicated `worker-dist/` directory from an explicit public-file allowlist, then fingerprint and verify its assets before Wrangler uploads them. The Worker asset directory contains only the seven public pages, generated CSS/JavaScript bundles, public `assets/`, and `media-library/`; repository-only content such as `.github/`, `tests/`, `scripts/`, and `supabase/` is excluded. The Pages-only `_headers` file is not copied into the Worker package. The Worker wrapper applies the same CSP, response-security headers, admin/client-gallery `no-store` policy, and fingerprint-aware immutable caching on the `workers.dev` mirror.

## HTTP security headers and cache integrity

The build injects one consistent CSP meta fallback into all seven deployed HTML pages. It then fingerprints local CSS, JavaScript, JSON, fonts, images, and media URLs with a 32-hex-character SHA-256 prefix (128-bit cache key). Any content change automatically changes the asset URL; the build verifies every local reference before deployment.

The root `_headers` file is included at the Cloudflare Pages static output root. Cloudflare Pages parses it into actual HTTP response headers for the seven static pages and assets. The policy sets HSTS, response CSP with `frame-ancestors`, clickjacking and MIME-sniffing protection, referrer and permissions policies, HTML revalidation, `no-store` for the admin and client-gallery pages, and one-year immutable caching for fingerprinted assets. Narrow cache rules detach the inherited Cache-Control header before applying route-specific values.

After every production deployment, `tests/toki-live-site-security-qa.py` fetches all seven pages and checks the actual returned headers, HTML cache behavior, fingerprinted same-origin assets, and the SHA-256 prefix against the live response bodies. The workflow sets `TOKI_REQUIRE_SECURITY_HEADERS=1`; any missing or incorrect response header, cache policy, or asset hash fails deployment verification.

### One-time origin verification

Add `toki-satsuei.pages.dev` to the allowed hostnames for the Cloudflare Turnstile widget used by the booking form. The Supabase `portfolio-submit` and `toki-calendar` Edge Functions now allow the exact Pages origin alongside the legacy personal-portfolio origin; they do not use wildcard CORS. For a future custom domain, add its exact origin to the Supabase Edge Function secret `PORTFOLIO_ADDITIONAL_ALLOWED_ORIGINS` (comma-separated), add that hostname to Turnstile, and set `TOKI_SITE_URL` to the same HTTPS origin. Turnstile still verifies the token hostname against the actual allowlisted request origin.

## Add photos and videos

Upload web-ready JPG, JPEG, PNG, WEBP, AVIF, GIF, MP4, or WEBM files into an album folder under `media-library/`.

Example: `media-library/cosplay/november-convention-2026/portrait-001.jpg`

The build scans those folders and generates `media-library.json` automatically. Do not upload private client-only files or camera RAW files to this public repository.

## Local testing

```bash
python -m pip install -r requirements-test.txt
python -m playwright install --with-deps chromium
python scripts/build-toki-media-library.py
python scripts/build-css.py
python scripts/build-css.py --check
python tests/toki-layout-browser-qa.py
python tests/toki-adaptive-interaction-qa.py
python tests/toki-scroll-motion-qa.py
python tests/toki-experience-design-qa.py
python tests/toki-public-pages-qa.py
python tests/toki-booking-browser-qa.py
python tests/toki-availability-calendar-qa.py
python tests/toki-cinematic-design-qa.py
python tests/toki-asset-integration-qa.py
python tests/toki-css-bundle-qa.py
python tests/toki-orientation-qa.py
python tests/toki-pricing-calculator-qa.py
python tests/toki-admin-dashboard-qa.py
python tests/toki-client-gallery-qa.py
python tests/toki-email-notification-qa.py
python tests/toki-security-static-qa.py
python tests/toki-live-http-security-qa.py
```

## Booking, privacy, and image consent

The public [booking and photo policies](https://toki-satsuei.pages.dev/policies.html) describe how requests are reviewed, how prices and payment terms are agreed, how schedule changes are handled, how files are delivered, and how client photographs may be shared. The standalone `booking.html` page sends the details you choose to provide to a Supabase Edge Function, which stores them in the private `public.toki_booking_requests` table. Anonymous visitors cannot read or insert directly into that table; the server-side intake is rate-limited and the owner dashboard reads requests under administrator-only Row Level Security. New requests are not reservations, do not hold a date, and do not request payment. Booking administration is handled directly in the Supabase Dashboard. Use the read-only `public.toki_booking_inbox` view to inspect requests and edit the underlying `public.toki_booking_requests` table. No personal-portfolio dashboard is used for TOKI bookings. Client photographs are not added to the public portfolio without permission from the people featured.

The site currently labels its existing gallery images as practice/detail studies. It does not claim to have a finished public cosplay or portrait client portfolio yet.

## Media and typography hosting

The official TOKI SATSUEI brushstroke logo remains an unchanged local master under `assets/brand/`. The four approved public practice photographs are now hosted from this repository under `assets/photography/originals/`; their JPEG and WebP derivatives are served from the same origin at 480px, 960px, and source width. `assets/photography/manifest.json` records image dimensions, aspect ratios, alternative text, byte sizes, and SHA-256 checksums. The build and QA preserve the original JPEG masters byte-for-byte, keep the homepage hero eager-loaded with high fetch priority, and lazy-load below-the-fold gallery images. The gallery lightbox continues to open the untouched originals.

Typography is self-hosted as local WOFF2 files under `assets/fonts/`, with SIL Open Font License files retained in `assets/fonts/licenses/`. The shared Cormorant Garamond, DM Sans, and Space Mono faces are included in each page bundle; Caveat is included only in the homepage/booking and 404 bundles. Production pages do not rely on `media.base44.com` or Google Fonts for these visual assets. Private client delivery photographs remain outside the public asset set.

## Public monthly availability calendar

The homepage includes a live monthly calendar backed by the separate `toki-calendar` Supabase Edge Function. The private owner queue stores the final `confirmed_date`, `confirmed_start_time`, and `confirmed_end_time` separately from the original preferred and alternate choices. A database check prevents a booking from entering `confirmed` status without a complete, valid time window, and a GiST exclusion constraint rejects overlapping confirmed sessions while allowing multiple bookings on the same date when their windows do not overlap. The public endpoint reads only the confirmed date and start/end times, applies an HMAC-derived per-network quota through the existing atomic quota function, and returns time windows without customer identity or private booking fields. Visitors can select a partially booked date to see its existing time windows and still send an inquiry for another time. The calendar supports a current-month shortcut, keyboard date movement, selected-date preview, explicit inquiry prefill, retry after network errors, automatic one-minute refresh, and Manila-local month rollover. Displayed times use Philippine time. An unmarked time window is not a guaranteed availability promise; all sessions still require written confirmation.

## Stylesheet source architecture

Editable CSS lives under styles/. The shared design system is split into styles/tokens.css (design tokens and build-time breakpoint tokens), styles/base.css (typography, accessibility, and layout foundations), and styles/components.css (reusable controls and components). Cross-page legacy layers are grouped under styles/shared/; page-owned styling is under styles/pages/. The exact source order for each page is defined in scripts/build-css.py.

The builder expands named @custom-media breakpoints into ordinary browser @media queries, then generates the six committed toki-*.css bundles. Every page still requests exactly one stylesheet. Source modules are not loaded individually by visitors. See styles/README.md before changing source ownership or bundle order.

The production workflow regenerates all six bundles from these source modules before running stylesheet QA and assembling the Pages/Workers artifacts. The static-site preflight then checks that the generated bundles are current. This prevents stale generated CSS from blocking packaging and ensures the deployed artifact reflects the checked-in source order. For local work, regenerate with `python scripts/build-css.py` before running `python scripts/build-css.py --check`.

## Runtime integration map

The site is delivered as seven static pages backed by unified bundled CSS (scripts/build-css.py), shared progressive motion/effects, and modular JavaScript controllers:

| File | Used by | Responsibility |
| --- | --- | --- |
| `toki-home.css`, `toki-archive.css`, `toki-policies.css`, `toki-404.css`, `toki-admin.css`, `toki-client.css` | All pages | Validated page bundles compiled by scripts/build-css.py from the shared design-system modules, ordered cross-page layers in styles/shared/, and page-specific modules in styles/pages/ |
| `motion-system.js` | Home, booking, archive, policies, admin, client gallery | Official-logo aperture intro, six reveal profiles, scroll-linked chapter rails and bounded image parallax, pointer tilt, shutter feedback, menu, and dialog helpers |
| `site.js` | Home, booking, archive, and policies | Navigation, page progress, interactive pricing calculator + booking sheet synchronization, Web Audio feedback, and Supabase intake relay |
| `styles/pages/availability.css` + `availability.js` | `index.html` | Public monthly calendar, confirmed-date feed, Manila month rollover, inquiry prefill, and minute refresh |
| `site.js` + `booking.html` | Dedicated desktop/mobile booking form, secure request submission, and cross-page package, calculator, and calendar prefill |
| `library.js` | `library.html` | Archive filters, search, media manifest, and album viewer |
| `admin.js` + `admin.html` | Studio operations console | Authenticated booking inbox management, pricing/add-ons inspection, confirmation windows, and token generation |
| `client-gallery.js` + `client-gallery.html` | Private client gallery | Token-gated photo delivery and client favorite selection |
| `media-library.json` + `media-library/` | `library.html` | Generated archive index and uploaded media |

Scripts load with `defer` in dependency order: shared motion first, shared page behavior second, and page-specific behavior last. Controllers are scoped so local declarations cannot collide. The archive manifest separates image, video, and total-media counts; the interface labels the combined count as items instead of treating videos as photographs. Every HTML asset reference, bundle checksum, test runner entry in `.github/workflows/deploy.yml`, and backend migration stays synchronized and is verified by `tests/toki-asset-integration-qa.py` and `tests/toki-css-bundle-qa.py`. Empty category folders under `media-library/` are intentional upload shelves, not unused assets.


## Booking form human verification

The booking form uses Cloudflare Turnstile with the `toki_booking` action and the `toki-satsuei.pages.dev` hostname (plus any explicitly configured custom domain). The browser sends the short-lived challenge token to the `portfolio-submit` Edge Function; Supabase verifies it with Cloudflare Siteverify before a booking is stored. Missing, invalid, expired, incorrectly scoped, or unverifiable booking tokens are rejected. TOKI booking verification fails closed when its dedicated server-side secret is not configured. The shared personal portfolio keeps its existing `TURNSTILE_SECRET_KEY` for inquiry and comment challenges.

### One-time owner setup

1. Create a Cloudflare Turnstile widget restricted to `toki-satsuei.pages.dev` and any explicitly configured production custom domain.
2. Keep the site key in the public form markup in `booking.html`; it is designed to be public.
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


## Motion and transition system

The motion implementation has one runtime source of truth: motion-system.js, its core stylesheet styles/shared/motion-system.css, and shared refinements in styles/shared/motion-refinements.css and styles/shared/global-motion.css. Scroll scenes receive a single active focal state, section progress, and bounded image parallax through the shared runtime. The active chapter marker is decorative and does not carry essential information.

Cross-document view transitions progressively enhance supported browsers and preserve the masthead as a shared visual element. They do not replace normal navigation. Reduced-motion preferences disable the page transition and scroll-linked effects; constrained devices also skip continuous grain and ambient overlay work.

Edit the source stylesheets, then run `python scripts/build-css.py` to regenerate all six `toki-*.css` page bundles. Do not hand-edit generated bundles. The scroll-motion browser QA checks each page—including the 404 page—for runtime integration, scene behavior, responsive overflow, reduced-motion parity, and current asset references.


### Client delivery portal

The client portal validates delivery keys and opens the private delivery URL configured by the studio. The destination must use HTTPS; the portal does not depend on a particular third-party storage provider. It does not display practice images as client photographs. An in-page proofing grid remains hidden until a real, server-provided photo manifest is connected to the delivery record. Access keys are entered into the password field and are not accepted in query strings.
