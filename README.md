# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio. A shared editorial design system keeps the homepage and archive visually consistent across screen sizes and orientations.

- **Live site:** https://legioniz.github.io/toki-satsuei/
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included

- Homepage, services, session guide, FAQs, and inquiry form
- Public booking, payment, rescheduling, privacy, and photo-consent guidelines
- Branded 404 page, `robots.txt`, and XML sitemap for search discovery
- Curated Facebook post rail with native Meta embeds, category filters, and search
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
python tests/toki-facebook-embed-qa.py
python tests/toki-facebook-feed-data-qa.py
python tests/toki-public-pages-qa.py
python tests/toki-booking-browser-qa.py
python tests/toki-availability-calendar-qa.py
python tests/toki-cinematic-design-qa.py
python tests/toki-asset-integration-qa.py
```

## Booking, privacy, and image consent

The public [booking and photo policies](https://legioniz.github.io/toki-satsuei/policies.html) describe how requests are reviewed, how prices and payment terms are agreed, how schedule changes are handled, how files are delivered, and how client photographs may be shared. The inquiry form sends the details you choose to provide to a Supabase Edge Function, which stores them in the private `public.toki_booking_requests` table. Anonymous visitors cannot read or insert directly into that table; the server-side intake is rate-limited and the owner dashboard reads requests under administrator-only Row Level Security. New requests are not reservations, do not hold a date, and do not request payment. The TOKI BOOKINGS view is available in the private Legioniz portfolio owner console. Client photographs are not added to the public portfolio without permission from the people featured.

The site currently labels its existing gallery images as practice/detail studies. It does not claim to have a finished public cosplay or portrait client portfolio yet.

## Media note

The official TOKI SATSUEI brushstroke logo and the current hero/sample gallery photographs are referenced directly from their original hosted media CDN assets. The logo is used unchanged: the site does not redraw, recolor, or generate a replacement. The website source and upload-ready archive structure remain independent in this repository; those original hosted image files have not been copied into Git because the available GitHub file-transfer connection cannot retrieve the binary media. New archive uploads can be stored directly in this repository under `media-library/`.

## Facebook post collection

The homepage contains a dedicated, horizontally scrollable collection of individual public Facebook posts. Visitors can swipe or scroll sideways through the posts on touchscreens and trackpads, use the previous/next controls, search by label or category, and filter by category. Each item is embedded directly from Facebook, preserving the original post's media, reactions, comments, and sharing controls where Facebook allows the embed to load.

To add posts, send the website maintainer the individual public Facebook post links. Those links are integrated into `facebook-posts.json` and published with the next website update. There is no public Feed Manager page or on-site publishing interface.

Use individual post permalinks copied from the Facebook post menu—not the Page homepage. Public posts, Reels, and supported video posts may embed. Stories are not displayed as post embeds; the website's Stories shortcut opens the Facebook Page. Private, deleted, age-restricted, or audience-limited posts may fail to display, and visitors may need to sign in or allow Facebook cookies.

Only up to 12 posts are included at once to keep the collection focused and the page manageable. The order in `facebook-posts.json` is the display order on the website.

Official references:
- [Meta Embedded Posts / Social Plugins](https://developers.facebook.com/docs/plugins/embedded-posts/)
- [Meta Graph API — oEmbed Post](https://developers.facebook.com/docs/graph-api/reference/oembed-post/)
- [Meta's official Meta Embeds WordPress plugin](https://github.com/facebook/meta-embeds-for-wordpress)


## Public monthly availability calendar

The homepage includes a live monthly calendar backed by the separate `toki-calendar` Supabase Edge Function. The private owner queue stores the final `confirmed_date`, `confirmed_start_time`, and `confirmed_end_time` separately from the original preferred and alternate choices. A database check prevents a booking from entering `confirmed` status without a complete, valid time window, and a GiST exclusion constraint rejects overlapping confirmed sessions while allowing multiple bookings on the same date when their windows do not overlap. The public endpoint reads only the confirmed date and start/end times, applies an HMAC-derived per-network quota through the existing atomic quota function, and returns time windows without customer identity or private booking fields. Visitors can select a partially booked date to see its existing time windows and still send an inquiry for another time. The calendar supports a current-month shortcut, keyboard date movement, selected-date preview, explicit inquiry prefill, retry after network errors, automatic one-minute refresh, and Manila-local month rollover. Displayed times use Philippine time. An unmarked time window is not a guaranteed availability promise; all sessions still require written confirmation.

## Runtime integration map

The site is delivered as four static pages with shared behavior and page-specific controllers:

| File | Used by | Responsibility |
| --- | --- | --- |
| `styles.css`, `refinement.css`, `cinematic.css`, `motion-system.css` | All public pages | Foundation, refinements, cinematic art direction, and shared motion |
| `library.css` | `library.html` | Archive layout and album presentation |
| `policies.css` | Home, policies, and 404 pages | Policy-page and shared long-form page details |
| `motion-system.js` | Home, archive, and policies | Shared motion, menu, and dialog helpers |
| `site.js` | Home, archive, and policies | Shared navigation, header behavior, page progress, and home-page interactions |
| `availability.css` + `availability.js` | `index.html` | Public monthly calendar, confirmed-date feed, Manila month rollover, inquiry prefill, and minute refresh |
| `library.js` | `library.html` | Archive filters, search, media manifest, and album viewer |
| `facebook-feed.js` + `facebook-posts.json` | `index.html` | Curated Facebook embeds and feed controls |
| `media-library.json` + `media-library/` | `library.html` | Generated archive index and uploaded media |

Scripts load with `defer` in dependency order: shared motion first, shared page behavior second, and page-specific behavior last. Controllers are scoped so local declarations cannot collide. The archive manifest separates image, video, and total-media counts; the interface labels the combined count as items instead of treating videos as photographs. The asset-integration QA verifies local links, script ordering, runtime data dependencies, media-manifest totals, stylesheet/script usage, and the standalone Pages package. Empty category folders under `media-library/` are intentional upload shelves, not unused assets.


## Free private booking alerts and owner log via Make

The website keeps its existing custom booking form. The Supabase `portfolio-submit` Edge Function saves each TOKI booking in the private `toki_booking_requests` table first, then makes a best-effort HTTPS call to a private Make.com Custom Webhook. Make can add the booking to a private Google Sheet and send an administrative email through the owner's connected Google account. A Make, Sheets, or Gmail failure never rolls back a saved booking.

### One-time owner setup

1. In Make, create a scenario with **Webhooks → Custom webhook** and copy its generated URL.
2. Add **Google Sheets → Add a Row** and select a spreadsheet that is private to the TOKI owner. Suggested columns: received time, reference code, name, contact method, contact detail, session, preferred date, alternate date, preferred time, location, participants, and notes.
3. Add **Gmail → Send an Email** and connect the owner's Google account. Send the alert to the private owner inbox. Map the booking fields from the Custom Webhook module's `booking` object.
4. Keep the scenario private and switch it on after the module mappings are complete.
5. In Make's Custom Webhook settings, optionally enable **API Key authentication** and create a key. This is recommended; Make requires that key in the `x-make-apikey` request header.
6. In the Supabase Dashboard for project `pjuwrngnrrvdiwqspkic`, open **Edge Functions → Secrets** and add:
   - `TOKI_EMAIL_WEBHOOK_URL`: the Make Custom Webhook URL.
   - `TOKI_EMAIL_WEBHOOK_API_KEY`: the Make API key, only when API Key authentication is enabled.
7. Send a test webhook while the Make scenario is in **Run once**, confirm the incoming field structure, then map and test both the Sheets row and Gmail email. Afterward, submit one real test booking with your own test contact details and verify that it appears in Supabase, Sheets, and the owner inbox.

Never put the webhook URL or API key in website JavaScript, a public repository, screenshots, or a public spreadsheet. Keep the spreadsheet and Make scenario restricted to the owner. The booking details contain personal contact information and are passed to Make and Google only for this owner-side workflow.

Make's default webhook response is HTTP 200 with plain-text `Accepted`. The backend treats that as queued for processing, not proof that the later email and spreadsheet modules succeeded. Add error notifications in Make and periodically check scenario execution history. New bookings remain saved in Supabase even if the Make workflow fails.

The source of the Supabase intake function is tracked at `supabase/functions/portfolio-submit/index.ts` in this repository. This function is shared with the main Legioniz portfolio backend; the Make notification call runs only for `kind: "toki_booking"` requests.
