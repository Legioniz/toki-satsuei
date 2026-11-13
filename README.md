# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio. A shared editorial design system keeps the homepage and archive visually consistent across screen sizes and orientations.

- **Live site:** https://legioniz.github.io/toki-satsuei/
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included

- Homepage, services, session guide, and inquiry form
- Curated Facebook post rail with native Meta embeds, category filters, and search
- Responsive photo archive with search, category rails, and album viewer
- Shared editorial design system for layout, spacing, color grading, responsive orientation, and visual consistency
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
```

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
