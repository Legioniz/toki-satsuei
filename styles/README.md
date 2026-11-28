# TOKI stylesheet source architecture

TOKI keeps one generated stylesheet per visitor-facing page. The browser does not
load source modules individually; `scripts/build-css.py` flattens them into the
committed `toki-*.css` bundles and preserves the established cascade order.

## Shared design system

- `tokens.css` — core color, type-scale, spacing, radius, shadow, sizing, named
  breakpoints, and motion tokens. The build expands source-only custom-media
  tokens so browsers receive ordinary media queries.
- `base.css` — baseline typography, accessibility defaults, reading rhythm,
  and layout foundations.
- `components.css` — shared controls, navigation, cards, forms, interaction
  states, adaptive behavior, and component-system refinements.

## Cross-page styles

`styles/shared/` contains cross-page foundation, refinements, cinematic
presentation, motion, orientation, compatibility, and navigation layers.
Homepage and booking-only experience styling lives in
`styles/pages/home-booking.css` and is emitted only in the shared home/booking
bundle. Shared layers remain separate where their relative order affects the
current cascade.

## Page styles

`styles/pages/` owns page-specific and page-family styling: homepage/booking,
availability, policies, pricing calculator, equipment viewer, archive, admin,
client gallery, and the shared archive/policy/404 page shells.

## Migration and cascade policy

The folder structure establishes ownership without pretending that every older
rule has already been deduplicated. CSS bundle QA now rejects byte-equivalent
rules repeated within the same source module and at-rule context. Non-identical
repeated selectors and historical `!important` declarations remain a separate
cascade-cleanup task: do not remove them or reorder shared layers by filename
alone. Migrate those rules only with computed-style and responsive/browser
regression checks.

## Build contract

Edit source modules, then run:

```sh
python scripts/build-css.py
python tests/toki-css-bundle-qa.py
```

The bundle manifest retains the historical source order and logical source
labels used by existing QA. The build flattens all sources at build time, so
visitors still request one generated CSS file per page; no runtime CSS
`@import` requests are introduced. Named `@custom-media` tokens are expanded
into browser-safe `@media` conditions during generation.

## Typography

The primary system uses Cormorant Garamond for editorial display, DM Sans for
body/interface copy, and Space Mono for technical labels. Caveat is reserved for
the handwritten homepage annotations and 404 art. It is only requested on the
homepage and 404 route. Space Grotesk has been retired in favor of the
already-loaded DM Sans.

## Self-hosted typography

The CSS build includes `assets/fonts/fonts.css` in every page-scoped bundle and `assets/fonts/fonts-caveat.css` only in the homepage/404 bundles. The browser still requests exactly one stylesheet per page. These bundles declare same-origin Latin WOFF2 faces with `font-display: swap`; Caveat is declared only in the homepage bundle (shared with booking) and the 404 bundle, and is downloaded only on pages where it is actually used. SIL Open Font License files are retained under `assets/fonts/licenses/`. No page requests Google Fonts CSS or font binaries at runtime.
