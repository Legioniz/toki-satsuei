const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; frame-ancestors 'self'; script-src 'self' https://static.sketchfab.com https://challenges.cloudflare.com https://*.challenges.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https:; connect-src 'self' https://pjuwrngnrrvdiwqspkic.supabase.co https://challenges.cloudflare.com https://*.challenges.cloudflare.com https://*.cloudflareinsights.com; frame-src 'self' https://sketchfab.com https://*.sketchfab.com https://challenges.cloudflare.com https://*.challenges.cloudflare.com; upgrade-insecure-requests",
  "X-Frame-Options": "SAMEORIGIN",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "X-Permitted-Cross-Domain-Policies": "none",
};

const FINGERPRINT = /^[0-9a-f]{32}$/;
const IMMUTABLE_ASSET = /\.(?:css|js|json|png|jpe?g|webp|avif|svg|gif|mp4|webm|woff2?|ttf|otf|ico)$/i;

function cacheControl(url) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (
    path === "/admin.html" ||
    path === "/client-gallery.html" ||
    path === "/admin" ||
    path === "/client-gallery"
  ) {
    return "no-store";
  }

  const versions = url.searchParams.getAll("v");
  if (
    IMMUTABLE_ASSET.test(path) &&
    versions.length === 1 &&
    FINGERPRINT.test(versions[0])
  ) {
    return "public, max-age=31536000, immutable";
  }

  return "no-cache, max-age=0, must-revalidate";
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
      headers.set("Strict-Transport-Security", "max-age=31536000");
    }

    headers.set("Cache-Control", cacheControl(url));

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
