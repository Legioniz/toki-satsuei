# Original TOKI SATSUEI assets

This folder stores the official TOKI logo, submitted camera-angle masters, approved public photography, self-hosted fonts, and generated page CSS.

- `brand/Toki-Satsuei-Brushstroke-Emblem.png`: 500 × 500 transparent PNG, palette-optimized with alpha transparency preserved.
- `equipment/camera/`: five camera-angle PNG masters, each 362 × 320.
- `ASSET-MANIFEST.json`: source dimensions and SHA-256 checksums.
- `css/`: committed page-scoped CSS bundles generated from the editable modules in `src/styles/`.
- Browser JavaScript is authored in `src/js/` and copied by the static-site builder to `dist/assets/js/`; no duplicate runtime source is kept here.

The camera-angle images remain owner-submitted masters and must not be recompressed or upscaled. The logo is the current owner-approved web asset. Keep its canonical filename and transparency; do not upscale or recompress it.

Client portfolio and private gallery photographs are separate and were not modified.

## Public website photography and fonts

- `photography/originals/` stores the untouched JPEG masters for approved public practice photographs.
- `photography/` also contains responsive JPEG and WebP derivatives at 480px, 960px, and source width, plus a manifest with dimensions, aspect ratios, alt text, byte sizes, and SHA-256 hashes.
- `fonts/` contains self-hosted Latin WOFF2 faces, the `fonts.css` shared source module, the `fonts-caveat.css` handwritten-only source module, a manifest, and SIL Open Font License files for Caveat, Cormorant Garamond, DM Sans, and Space Mono. The shared font faces are bundled into every page stylesheet; Caveat is bundled only in the homepage (shared with booking) and 404 page CSS. No separate font stylesheet request is made.
- Regenerate from the approved sources with `python scripts/import_site_media.py`; verify without network access using `python scripts/import_site_media.py --verify-only`.
- Do not replace original masters with resized or recompressed derivatives. Private client deliveries remain outside this public asset set.
