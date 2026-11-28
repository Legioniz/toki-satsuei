# Original TOKI SATSUEI assets

This folder stores the original camera-angle PNGs and official brushstroke emblem supplied by the owner.

- `brand/Toki-Satsuei-Brushstroke-Emblem.png`: 1254 × 1254 PNG.
- `equipment/camera/`: five camera-angle PNG masters, each 362 × 320.
- `ASSET-MANIFEST.json`: source dimensions and SHA-256 checksums.

These are master assets. Do not overwrite, lossy-convert, or upscale them. The site displays the camera angles at or below their native 362px width. The logo master has sufficient resolution for the website's current display sizes.

Client portfolio and private gallery photographs are separate and were not modified.

## Public website photography and fonts

- `photography/originals/` stores the untouched JPEG masters for approved public practice photographs.
- `photography/` also contains responsive JPEG and WebP derivatives at 480px, 960px, and source width, plus a manifest with dimensions, aspect ratios, alt text, byte sizes, and SHA-256 hashes.
- `fonts/` contains self-hosted Latin WOFF2 faces, the generated `fonts.css` source module, a manifest, and SIL Open Font License files for Caveat, Cormorant Garamond, DM Sans, and Space Mono. The font-face source is incorporated into each page-scoped CSS bundle at build time; it is not loaded as a second stylesheet.
- Regenerate from the approved sources with `python scripts/import_site_media.py`; verify without network access using `python scripts/import_site_media.py --verify-only`.
- Do not replace original masters with resized or recompressed derivatives. Private client deliveries remain outside this public asset set.
