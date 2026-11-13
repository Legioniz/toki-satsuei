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
The homepage uses Meta's official Page Plugin iframe rather than scraping or copying posts. The embed is measured against its column, constrained to the plugin's supported 180–500 px width, and re-rendered only when the column width changes. The feed is lazy-loaded and a direct Page link remains available when Facebook blocks an embed or asks a visitor to sign in. Automated tests mock the cross-origin plugin so responsive sizing and fallback behavior can be checked reliably without depending on Facebook's availability during CI.
