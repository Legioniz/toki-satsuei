import assert from "node:assert/strict";
import worker from "../src/worker/worker.mjs";

async function request(path, assetResponse = new Response("ok")) {
  return worker.fetch(
    new Request("https://toki-satsuei.kingartriez.workers.dev" + path),
    { ASSETS: { fetch: async () => assetResponse } },
  );
}

const html = await request("/");
assert.equal(html.status, 200);
assert.equal(html.headers.get("strict-transport-security"), "max-age=31536000");
assert.equal(html.headers.get("x-frame-options"), "SAMEORIGIN");
assert.equal(html.headers.get("x-content-type-options"), "nosniff");
assert.equal(html.headers.get("referrer-policy"), "strict-origin-when-cross-origin");
assert.equal(html.headers.get("permissions-policy"), "camera=(), microphone=(), geolocation=()");
assert.match(html.headers.get("content-security-policy") ?? "", /frame-ancestors 'self'/);
assert.equal(html.headers.get("cache-control"), "no-cache, max-age=0, must-revalidate");

const admin = await request("/admin.html");
assert.equal(admin.headers.get("cache-control"), "no-store");

const clientGallery = await request("/client-gallery");
assert.equal(clientGallery.headers.get("cache-control"), "no-store");

const fingerprinted = await request("/assets/css/toki-home.css?v=0123456789abcdef0123456789abcdef");
assert.equal(fingerprinted.headers.get("cache-control"), "public, max-age=31536000, immutable");

const unversioned = await request("/assets/logo.png");
assert.equal(unversioned.headers.get("cache-control"), "no-cache, max-age=0, must-revalidate");

const notFound = await request("/missing-resource", new Response("not found", { status: 404 }));
assert.equal(notFound.status, 404);
assert.equal(notFound.headers.get("x-content-type-options"), "nosniff");

console.log("PASS TOKI Worker runtime QA: CSP/security headers, HTTPS HSTS, admin/gallery no-store, fingerprinted immutable assets, and safe default caching.");
