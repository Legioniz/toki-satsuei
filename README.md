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
python tests/toki-cinematic-design-qa.py
python tests/toki-asset-integration-qa.py
```

## Booking, privacy, and image consent

The public [booking and photo policies](https://legioniz.github.io/toki-satsuei/policies.html) describe how inquiries are confirmed, how prices and payment terms are agreed, how schedule changes are handled, how files are delivered, and how client photographs may be shared. The inquiry form only prepares and copies a message in the visitor's browser; it does not submit personal information to a server. Client photographs are not added to the public portfolio without permission from the people featured.

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


## Runtime integration map

The site is delivered as four static pages with shared behavior and page-specific controllers:

| File | Used by | Responsibility |
| --- | --- | --- |
| `styles.css`, `refinement.css`, `cinematic.css`, `motion-system.css` | All public pages | Foundation, refinements, cinematic art direction, and shared motion |
| `library.css` | `library.html` | Archive layout and album presentation |
| `policies.css` | Home, policies, and 404 pages | Policy-page and shared long-form page details |
| `motion-system.js` | Home, archive, and policies | Shared motion, menu, and dialog helpers |
| `site.js` | Home, archive, and policies | Shared navigation, header behavior, page progress, and home-page interactions |
| `library.js` | `library.html` | Archive filters, search, media manifest, and album viewer |
| `facebook-feed.js` + `facebook-posts.json` | `index.html` | Curated Facebook embeds and feed controls |
| `media-library.json` + `media-library/` | `library.html` | Generated archive index and uploaded media |

Scripts load with `defer` in dependency order: shared motion first, shared page behavior second, and page-specific behavior last. Controllers are scoped so local declarations cannot collide. The archive manifest separates image, video, and total-media counts; the interface labels the combined count as items instead of treating videos as photographs. The asset-integration QA verifies local links, script ordering, runtime data dependencies, media-manifest totals, stylesheet/script usage, and the standalone Pages package. Empty category folders under `media-library/` are intentional upload shelves, not unused assets.
