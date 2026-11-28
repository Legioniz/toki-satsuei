# Test suites

The `toki-*-qa.py` and `toki-*-qa.mjs` files are organized by feature: asset/build integration, responsive layout, browser interactions, booking, availability, archive/media, security, and deployment packaging.

- `support/` holds the local HTTPS server helpers used by Playwright and Lighthouse.
- Browser tests serve the generated `dist/` site so they exercise the same public paths as the deploy artifact.
- Source-level assertions read authored files under `src/`, while the workflow generates `dist/` before executing browser QA.

Run the complete production verification workflow from a pull request; local setup instructions are in the root `README.md`.
