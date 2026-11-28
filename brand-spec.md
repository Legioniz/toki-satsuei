# TOKI SATSUEI brand spec

## Brand assets

- Official logo master: `assets/brand/Toki-Satsuei-Brushstroke-Emblem.png` (submitted 1254 × 1254 PNG; stored unchanged).
- Hero / behind-the-camera image: `assets/photography/originals/behind-the-camera.jpg`
- Field study images:
  - `assets/photography/originals/between-turns.jpg`
  - `assets/photography/originals/colour-in-the-quiet.jpg`
  - `assets/photography/originals/before-the-next-shot.jpg`

## Photography asset pipeline

- Approved public photography masters are retained byte-for-byte under `assets/photography/originals/`.
- Responsive JPEG and WebP derivatives are generated at 480px, 960px, and source width (1536px) without cropping or upscaling.
- `assets/photography/manifest.json` records dimensions, aspect ratio, alternative text, file sizes, and SHA-256 checksums for originals and variants.
- Site delivery uses the same-origin Cloudflare Pages asset path. Below-the-fold gallery thumbnails are lazy-loaded; the homepage hero is eagerly loaded with high fetch priority.

## Equipment source assets

- Camera angles: `assets/equipment/camera/` — five submitted PNG masters, each 362 × 320, retained byte-for-byte.
- The equipment viewer renders these images at or below native width; it does not upscale low-resolution sources.
- Client portfolio and private gallery photographs remain on their existing sources and are not modified by this asset update.

## Visual system

- Mode: Unified Darkroom Studio Design System (`design-system.css` + bundled `toki-*.css`).
- Palette: OLED black (`#09090b`), warm archival paper (`#ede7dc`), charcoal surfaces, crimson accent `#A31F2D` / `#C32A39`, and warm brass/gold `#d8a448` / `#ecc77e`.
- Display type: Cormorant Garamond (`0.94–1.02` line-height) for editorial headlines; DM Sans (`>=15px` body floor) for effortless prose reading.
- UI and metadata: Space Mono (`>=12.5px`) for labels, telemetry controls, pricing math, and calendar indicators.
- Spacing & layout: 8pt spacing tokens, spacious full-width booking sheet, clean matte backgrounds free of distracting ruled lines behind prose.
- Motion: Optical darkroom viewfinder HUD, shutter flash curtain, 3D tilt cards, film sprocket parallax, and reduced-motion parity (`prefers-reduced-motion: reduce` keeps static vector geometry visible without vestibular movement).

## Protected contracts

- Official logo and hosted photography remain unchanged.
- Existing anchors, archive/policy URLs, booking field names, consent wording, and booking-integrity rules remain unchanged.
- The site continues to describe the current public gallery as practice/detail studies until permissioned client work is available.
