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

`styles/shared/` contains existing styles used across multiple page bundles:
the original foundation, refinements, cinematic treatments, booking experience,
motion system, orientation rules, compatibility fixes, and navigation. These
layers remain separate because their relative order affects the current visual
cascade. They are now grouped by shared ownership rather than mixed with
page-owned styles.

## Page styles

`styles/pages/` owns page-specific and page-family styling: availability,
policies, pricing calculator, equipment viewer, archive, admin, client gallery,
and the shared archive/policy/404 page shells.

## Migration and cascade policy

The folder structure establishes ownership without pretending that every older
rule has already been deduplicated. Some shared files still contain historical
overrides and `!important` declarations. Do not remove them or reorder shared
layers by filename alone. Migrate duplicate selectors into tokens/base/components
only with computed-style and responsive/browser regression checks.

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
