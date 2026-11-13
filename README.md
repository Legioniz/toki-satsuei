# TOKI SATSUEI — Photography portfolio

The complete standalone TOKI SATSUEI website, kept separate from the Legioniz personal portfolio.

- **Live site:** https://legioniz.github.io/toki-satsuei/
- **Facebook:** https://www.facebook.com/tokisatsuiephotography/
- **Instagram:** https://www.instagram.com/tokisatsuiephotography/

## Included
- Homepage, service guide, session packages, and inquiry form
- Embedded live-updating Facebook Page timeline
- Responsive photo archive with search, category rails, and album viewer
- TOKI brand SVG, media-library upload folders, and archive manifest generator
- Dedicated GitHub Pages workflow and browser regression tests

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
```

## Media note
The current hero, sample gallery photographs, and main brushstroke emblem are referenced from the original hosted media CDN. The portfolio source and its upload-ready archive structure are independent in this repository; those existing hosted image files have not been copied into Git because the available file-transfer connection cannot retrieve the original binary media. New archive uploads can be stored directly in this repository under `media-library/`.
