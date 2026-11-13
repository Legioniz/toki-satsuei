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


## Curated Facebook post feed

The homepage displays selected public Facebook posts as individual Meta post embeds. This avoids the unreliable Page timeline discovery approach: each post is added deliberately by URL, and Facebook retains the original content, reactions, comments, and sharing controls inside its embed. Only public posts can be embedded; private, removed, age-restricted, or audience-limited posts may fail to display.

### Add or remove posts

1. Open the site's **Manage Posts** link or visit https://legioniz.github.io/toki-satsuei/feed-manager.html.
2. Copy the link for an individual public post from the TOKI SATSUEI Facebook Page and add it to the manager. You can reorder or remove saved links.
3. Select **Copy Updated JSON**, then open the GitHub editor for [facebook-posts.json](https://github.com/Legioniz/toki-satsuei/edit/main/facebook-posts.json).
4. Replace the file contents with the copied JSON and commit the change. GitHub Actions tests and deploys the updated site.

The manager does not require Meta developer credentials or store a Facebook token. It prepares a change for the static file; committing through GitHub is the save/publish step. Up to 12 posts can be curated. The order in the manager is the display order on the website.

### Supported content

Use individual post permalinks, not the Page homepage. Copy the post link from Facebook's post menu. The individual Meta embed is rendered through the Facebook JavaScript SDK with fluid width and post text enabled. Stories are not supported as embedded posts; the Stories link opens the Page itself. Visitors may need to sign in or allow Facebook cookies depending on their browser settings.

Official references:
- [Meta Embedded Posts / Social Plugins](https://developers.facebook.com/docs/plugins/embedded-posts/)
- [Meta Graph API — oEmbed Post](https://developers.facebook.com/docs/graph-api/reference/oembed-post/) — Meta removed the access-token requirement for public Facebook oEmbed content on June 15, 2026; the oEmbed API needs a specific post URL and does not discover newest Page posts.
- [Meta's official Meta Embeds WordPress plugin](https://github.com/facebook/meta-embeds-for-wordpress) — confirms tokenless embedding of public Facebook post and Reel URLs.

### Local QA

- **python tests/toki-facebook-embed-qa.py**
- **python tests/toki-facebook-feed-data-qa.py**
