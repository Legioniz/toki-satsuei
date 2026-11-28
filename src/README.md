# Application source

- `js/` — authored browser controllers referenced by the public HTML pages through the built `assets/js/` path.
- `styles/` — editable stylesheet modules and their bundle-ownership documentation. Generated CSS is written to `assets/css/`.
- `worker/` — the Cloudflare Worker response-security wrapper. `wrangler.worker.jsonc` uses `src/worker/worker.mjs` as its entry point.

Public HTML route entrypoints intentionally remain at the repository root. The build copies JavaScript into `dist/assets/js/`; do not add a second committed copy there.
