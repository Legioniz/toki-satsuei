# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio.

- **Live site:** https://legioniz.github.io/toki-satsuei/
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included
- Homepage, services, session guide, and inquiry form
- Responsive Facebook Page timeline that recalculates its embed width on viewport and orientation changes, with a direct-Page fallback
- Responsive photo archive with search, category rails, and album viewer
- TOKI brand SVG, upload-ready media folders, and automatic archive manifest generator
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
```

## Media note
The current hero, sample gallery photographs, and main brushstroke emblem are referenced from the original hosted media CDN. The website source and its upload-ready archive structure are independent in this repository; those existing hosted image files have not been copied into Git because the available GitHub file-transfer connection cannot retrieve the original binary media. New archive uploads can be stored directly in this repository under `media-library/`.

## Facebook timeline behavior
The homepage uses Meta's official Page Plugin iframe rather than scraping or copying posts. The embed is measured against its column, constrained to 180–500 px, given a taller 980 px browsing area, and left natively scrollable so visitors can browse posts inside the frame. Facebook's own Like, comment, and share controls remain inside the embedded timeline and may require sign-in. A separate Stories shortcut opens the Page itself because Page Stories are not exposed as a separate Page Plugin tab; Facebook controls whether a current Story is visible. Automated tests mock the cross-origin plugin so responsive sizing, scroll settings, and the Stories hand-off can be checked reliably without depending on Facebook's availability during CI.


## Facebook public post feed

The homepage no longer depends on a third-party Page timeline iframe to render its feed. A scheduled GitHub Actions workflow retrieves the Page's own published posts from Meta's official Graph API and writes a small public facebook-feed.json snapshot. The browser renders post text and images as normal accessible site content; **React** and **Comment** open the original post, while **Share** opens Facebook's sharing flow. The Page's Stories shortcut still opens Facebook directly because Page Stories are not part of the Page Feed endpoint.

### One-time Meta connection

The repository is intentionally shipped without a Page token. To enable automatic posts:

1. In Meta for Developers, create or select an app and use an account that has the Page's content-management or moderation task.
2. Authorize the app for **pages_read_engagement**, **pages_read_user_content**, and **pages_show_list**; obtain the **Page access token** for the TOKI SATSUEI Page and its numeric Page ID. Meta may require app review / Page Public Content Access depending on the app and Page access context.
3. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - **META_PAGE_ID** — the Page's numeric ID
   - **META_PAGE_ACCESS_TOKEN** — the Page access token
4. Open **Actions → Refresh TOKI SATSUEI Facebook feed → Run workflow**. The feed is then refreshed automatically every six hours. The refresh workflow commits only the public post snapshot; the token is never committed or sent to the visitor's browser.

When the secrets are not configured, the homepage shows an explicit connection-needed message and a direct Page link instead of an empty or unresponsive box. When Meta temporarily rejects a refresh, the workflow preserves the last successful snapshot.

Official references:
- [Meta Page Feed endpoint](https://developers.facebook.com/docs/graph-api/reference/page/feed/)
- [Meta Page permissions and public Page access](https://developers.facebook.com/docs/graph-api/reference/page/)
- [Meta oEmbed Post](https://developers.facebook.com/docs/graph-api/reference/oembed-post/) — useful when embedding a known individual public post; it does not discover the Page's newest posts.

### Local QA

- **python tests/toki-facebook-feed-data-qa.py**
- **python tests/toki-facebook-embed-qa.py**
