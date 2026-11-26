// Public TOKI SATSUEI availability API.
// This endpoint reveals only unique confirmed calendar dates. The actual
// customer record remains private behind the owner-only RLS policies.

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const secretKeys = (() => {
  try {
    return JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
})();
const modernSecretKey = secretKeys.default ?? "";
const legacyServiceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const SERVICE_ROLE_KEY = modernSecretKey || legacyServiceRoleKey;
const USE_MODERN_SECRET = Boolean(modernSecretKey);
const RATE_SECRET = Deno.env.get("PORTFOLIO_RATE_LIMIT_SECRET") ?? SERVICE_ROLE_KEY;
const ALLOWED_ORIGIN = Deno.env.get("PORTFOLIO_ALLOWED_ORIGIN") ?? "https://legioniz.github.io";
const serviceKeyHeaders = {
  apikey: SERVICE_ROLE_KEY,
  ...(USE_MODERN_SECRET ? {} : { Authorization: "Bearer " + SERVICE_ROLE_KEY }),
};

type Booking = { date: string; start_time: string; end_time: string };
// The database quota uses fixed 10-minute windows.
const CALENDAR_LIMIT = 30;
const CALENDAR_WINDOW_SECONDS = 600;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$/;

function manilaMonth(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return part("year") + "-" + part("month");
}

function validMonth(value: string): boolean {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return false;
  const year = Number(value.slice(0, 4));
  return year >= 2000 && year <= 2100;
}

async function hmacHex(secret: string, value: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function consumeCalendarQuota(bucketHash: string): Promise<boolean> {
  const result = await fetch(SUPABASE_URL + "/rest/v1/rpc/consume_portfolio_quota", {
    method: "POST",
    headers: { ...serviceKeyHeaders, "Content-Type": "application/json" },
    body: JSON.stringify({
      p_bucket_hash: bucketHash,
      p_scope: "toki_calendar",
      p_limit: CALENDAR_LIMIT,
    }),
  });
  if (!result.ok) throw new Error("Calendar quota service unavailable");
  return await result.json() === true;
}

function corsHeaders(origin: string | null): Record<string, string> {
  return {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store, private",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Access-Control-Allow-Origin": origin === ALLOWED_ORIGIN ? ALLOWED_ORIGIN : "null",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "apikey, content-type, x-client-info",
    "Vary": "Origin",
  };
}

function jsonResponse(
  body: unknown,
  status: number,
  origin: string | null,
  extraHeaders: Record<string, string> = {},
): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), ...extraHeaders },
  });
}

function trustedClientAddress(request: Request): string | null {
  // Supabase Edge Functions are fronted by Cloudflare. Trust only the
  // Cloudflare-overwritten client IP; never accept caller-controlled XFF/X-Real-IP.
  const candidate = request.headers.get("cf-connecting-ip")?.trim() ?? "";
  if (candidate.length >= 2 && candidate.length <= 64 && /^[0-9a-fA-F:.]+$/.test(candidate)) return candidate;
  return null;
}

Deno.serve(async (request: Request) => {
  const origin = request.headers.get("origin");

  if (request.method === "OPTIONS") {
    if (origin !== ALLOWED_ORIGIN) {
      return jsonResponse({ ok: false, message: "Origin not allowed." }, 403, origin);
    }
    return jsonResponse({}, 204, origin);
  }
  if (request.method !== "GET") {
    return jsonResponse({ ok: false, message: "Method not allowed." }, 405, origin);
  }
  if (origin !== ALLOWED_ORIGIN) {
    return jsonResponse({ ok: false, message: "Origin not allowed." }, 403, origin);
  }
  if (!SUPABASE_URL || !SERVICE_ROLE_KEY || !RATE_SECRET || !ALLOWED_ORIGIN) {
    return jsonResponse({ ok: false, message: "Calendar service is not configured." }, 503, origin);
  }

  const requestedMonth = new URL(request.url).searchParams.get("month") ?? manilaMonth();
  if (!validMonth(requestedMonth)) {
    return jsonResponse({ ok: false, message: "Use a valid YYYY-MM month." }, 400, origin);
  }

  try {
    const forwarded = trustedClientAddress(request);
    if (!forwarded) {
      return jsonResponse({ ok: false, message: "Request protection is temporarily unavailable." }, 503, origin);
    }
    const bucketHash = await hmacHex(RATE_SECRET, forwarded);
    const allowed = await consumeCalendarQuota(bucketHash);
    if (!allowed) {
      return jsonResponse(
        { ok: false, message: "The calendar is receiving too many requests. Please retry in a moment." },
        429,
        origin,
        { "Retry-After": String(CALENDAR_WINDOW_SECONDS) },
      );
    }

    const year = Number(requestedMonth.slice(0, 4));
    const month = Number(requestedMonth.slice(5, 7));
    const startDate = requestedMonth + "-01";
    const nextMonthStart = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10);
    const filters = new URLSearchParams({
      select: "confirmed_date,confirmed_start_time,confirmed_end_time",
      status: "eq.confirmed",
      confirmed_date: "gte." + startDate,
      and: "(confirmed_date.lt." + nextMonthStart + ")",
      order: "confirmed_date.asc,confirmed_start_time.asc",
      limit: "1000",
    });

    const result = await fetch(SUPABASE_URL + "/rest/v1/toki_booking_requests?" + filters.toString(), {
      method: "GET",
      headers: { ...serviceKeyHeaders, Accept: "application/json" },
    });
    if (!result.ok) {
      console.error("TOKI calendar database query failed:", result.status);
      return jsonResponse({ ok: false, message: "Calendar data is temporarily unavailable." }, 502, origin);
    }

    const rows = await result.json();
    if (!Array.isArray(rows)) {
      return jsonResponse({ ok: false, message: "Calendar data is temporarily unavailable." }, 502, origin);
    }

    // Validate every row at the boundary; only well-formed time windows leave this function.
    const bookings: Booking[] = rows
      .flatMap((row: Record<string, unknown>): Booking[] => {
        const date = row.confirmed_date;
        const start = typeof row.confirmed_start_time === "string" ? row.confirmed_start_time.slice(0, 8) : "";
        const end = typeof row.confirmed_end_time === "string" ? row.confirmed_end_time.slice(0, 8) : "";
        if (typeof date !== "string" || !DATE_PATTERN.test(date) || date.slice(0, 7) !== requestedMonth) return [];
        if (!TIME_PATTERN.test(start) || !TIME_PATTERN.test(end) || start >= end) return [];
        return [{ date, start_time: start, end_time: end }];
      })
      .sort((a, b) => a.date.localeCompare(b.date) || a.start_time.localeCompare(b.start_time));

    // Keep this projection intentionally narrow: date and time window only.
    return jsonResponse({ ok: true, month: requestedMonth, bookings }, 200, origin);
  } catch (error) {
    console.error("TOKI calendar request failed:", error instanceof Error ? error.name : "unknown");
    return jsonResponse({ ok: false, message: "Calendar data is temporarily unavailable." }, 500, origin);
  }
});
