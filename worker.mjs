// BEGIN_SECURITY_POLICY
const SECURITY_HEADERS = {
  "Content-Security-Policy": "default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; frame-ancestors 'self'; script-src 'self' https://static.sketchfab.com https://challenges.cloudflare.com https://*.challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob: https:; connect-src 'self' https://pjuwrngnrrvdiwqspkic.supabase.co https://challenges.cloudflare.com https://*.challenges.cloudflare.com https://*.cloudflareinsights.com; frame-src 'self' https://sketchfab.com https://*.sketchfab.com https://challenges.cloudflare.com https://*.challenges.cloudflare.com; upgrade-insecure-requests",
  "X-Frame-Options": "SAMEORIGIN",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "X-Permitted-Cross-Domain-Policies": "none"
};
const HSTS_HEADER = "max-age=31536000";
const NO_STORE_PATHS = new Set([
  "/admin.html",
  "/client-gallery.html",
  "/admin",
  "/client-gallery"
]);
const DEFAULT_CACHE_CONTROL = "no-cache, max-age=0, must-revalidate";
const IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable";
// END_SECURITY_POLICY

const FINGERPRINT = /^[0-9a-f]{32}$/;
const IMMUTABLE_ASSET = /\.(?:css|js|json|png|jpe?g|webp|avif|svg|gif|mp4|webm|woff2?|ttf|otf|ico)$/i;

function cacheControl(url) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (NO_STORE_PATHS.has(path)) {
    return "no-store";
  }

  const versions = url.searchParams.getAll("v");
  if (
    IMMUTABLE_ASSET.test(path) &&
    versions.length === 1 &&
    FINGERPRINT.test(versions[0])
  ) {
    return IMMUTABLE_CACHE_CONTROL;
  }

  return DEFAULT_CACHE_CONTROL;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const response = await env.ASSETS.fetch(request);
    const headers = new Headers(response.headers);

    for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
      headers.set(name, value);
    }

    if (url.protocol === "https:") {
      headers.set("Strict-Transport-Security", HSTS_HEADER);
    }

    headers.set("Cache-Control", cacheControl(url));

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
