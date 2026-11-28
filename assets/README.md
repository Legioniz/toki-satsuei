# Original TOKI SATSUEI assets

This folder stores the original camera-angle PNGs and official brushstroke emblem supplied by the owner.

- `brand/Toki-Satsuei-Brushstroke-Emblem.png`: 1254 × 1254 PNG.
- `equipment/camera/`: five camera-angle PNG masters, each 362 × 320.
- `ASSET-MANIFEST.json`: source dimensions and SHA-256 checksums.

These are master assets. Do not overwrite, lossy-convert, or upscale them. The site displays the camera angles at or below their native 362px width. The logo master has sufficient resolution for the website's current display sizes.

Client portfolio and private gallery photographs are separate and were not modified.

## Public website photography and fonts

- `photography/originals/` holds the untouched approved JPEG masters for the four public practice photographs.
- `photography/` also holds responsive JPEG and WebP derivatives at 480px, 960px, and 1536px, plus a manifest with dimensions, aspect ratios, descriptive alt text, byte sizes, and SHA-256 hashes.
- `fonts/` holds self-hosted Latin WOFF2 faces, a font manifest, and the four SIL Open Font License files for Caveat, Cormorant Garamond, DM Sans, and Space Mono.
- The per-page generated CSS bundles declare the local font faces with `font-display: swap`; the HTML does not load Google Fonts at runtime.
- Do not replace master files with resized or recompressed derivatives. Private client gallery delivery remains outside this public asset set.
