// Supabase Edge Function: public inquiry/comment intake + consented page-view counts.
// Supabase injects SUPABASE_URL and SUPABASE_SECRET_KEYS into hosted Edge Functions.
// Only the public site origin is fixed here; no privileged key is stored in source control.
// Optional custom overrides: PORTFOLIO_ALLOWED_ORIGIN, PORTFOLIO_RATE_LIMIT_SECRET,
// and TURNSTILE_SECRET_KEY (the matching site key is a public Vite variable).

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') ?? ''
const secretKeys = (() => {
  try { return JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS') ?? '{}') as Record<string, string> }
  catch { return {} }
})()
const modernSecretKey = secretKeys.default ?? ''
const legacyServiceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
const SERVICE_ROLE_KEY = modernSecretKey || legacyServiceRoleKey
const USE_MODERN_SECRET = Boolean(modernSecretKey)
const ALLOWED_ORIGIN = Deno.env.get('PORTFOLIO_ALLOWED_ORIGIN') ?? 'https://legioniz.github.io'
const ALLOWED_HOSTNAME = (() => {
  try { return new URL(ALLOWED_ORIGIN).hostname }
  catch { return '' }
})()
const RATE_SECRET = Deno.env.get('PORTFOLIO_RATE_LIMIT_SECRET') ?? SERVICE_ROLE_KEY
const TURNSTILE_SECRET = Deno.env.get('TURNSTILE_SECRET_KEY') ?? ''
// Separate key for the TOKI widget so the shared personal-portfolio widget keeps its own secret.
const TOKI_TURNSTILE_SECRET = Deno.env.get('TOKI_TURNSTILE_SECRET_KEY') ?? ''

const serviceKeyHeaders = {
  apikey: SERVICE_ROLE_KEY,
  ...(USE_MODERN_SECRET ? {} : { Authorization: `Bearer ${SERVICE_ROLE_KEY}` }),
}

const jsonHeaders = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }

function response(body: unknown, status: number, origin: string | null) {
  const corsOrigin = ALLOWED_ORIGIN && origin === ALLOWED_ORIGIN ? ALLOWED_ORIGIN : 'null'
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: {
      ...jsonHeaders,
      'Access-Control-Allow-Origin': corsOrigin,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'authorization, apikey, content-type, x-client-info',
      'Vary': 'Origin',
    },
  })
}

async function hmacHex(secret: string, value: string) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(value))
  return Array.from(new Uint8Array(signature)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function consumeQuota(hash: string, scope: string, limit: number) {
  const result = await fetch(`${SUPABASE_URL}/rest/v1/rpc/consume_portfolio_quota`, {
    method: 'POST',
    headers: { ...serviceKeyHeaders, 'Content-Type': 'application/json' },
    body: JSON.stringify({ p_bucket_hash: hash, p_scope: scope, p_limit: limit }),
  })
  if (!result.ok) throw new Error('Rate-limit service unavailable')
  return await result.json() === true
}

async function verifyTurnstile(
  token: string,
  expectedAction: 'portfolio_inquiry' | 'portfolio_comment' | 'toki_booking',
  secret: string,
  failClosedWhenUnconfigured = false,
) {
  // Keep the personal portfolio's existing optional-secret behavior, but require
  // the TOKI booking secret. Any configured secret is always verified strictly.
  if (!secret) return !failClosedWhenUnconfigured
  if (!token || token.length > 2048 || !ALLOWED_HOSTNAME) return false
  const body = new URLSearchParams({ secret, response: token })
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  try {
    const result = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      body,
      signal: controller.signal,
    })
    if (!result.ok) return false
    const payload = await result.json() as { success?: boolean; hostname?: string; action?: string }
    return payload.success === true
      && payload.hostname === ALLOWED_HOSTNAME
      && payload.action === expectedAction
  } catch {
    return false
  } finally {
    clearTimeout(timeout)
  }
}

async function readLimitedBody(request: Request, maximumBytes: number): Promise<string | null> {
  const reader = request.body?.getReader()
  if (!reader) return ''
  const chunks: Uint8Array[] = []
  let totalBytes = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    totalBytes += value.byteLength
    if (totalBytes > maximumBytes) {
      await reader.cancel()
      return null
    }
    chunks.push(value)
  }
  const body = new Uint8Array(totalBytes)
  let offset = 0
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength }
  return new TextDecoder().decode(body)
}

function readText(value: unknown): string | null {
  return typeof value === 'string' ? value.trim() : null
}

function manilaToday(): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'Asia/Manila',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

function isValidDateOnly(value: string, notBefore: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(`${value}T00:00:00.000Z`)
  return Number.isFinite(parsed.getTime())
    && parsed.toISOString().slice(0, 10) === value
    && value >= notBefore
}

async function insertRecord(table: string, record: Record<string, unknown>, returning?: string) {
  const query = returning ? `?select=${encodeURIComponent(returning)}` : ''
  const result = await fetch(`${SUPABASE_URL}/rest/v1/${table}${query}`, {
    method: 'POST',
    headers: {
      ...serviceKeyHeaders,
      'Content-Type': 'application/json',
      Prefer: returning ? 'return=representation' : 'return=minimal',
    },
    body: JSON.stringify(record),
  })
  if (!result.ok) {
    const detail = await result.text()
    console.error(`Insert failed for ${table}:`, detail.slice(0, 500))
    throw new Error('The request could not be saved. Please retry or use the official contact channel listed on the website.')
  }
  return returning ? await result.json() as Array<Record<string, unknown>> : null
}


const TOKI_EMAIL_WEBHOOK_URL = Deno.env.get('TOKI_EMAIL_WEBHOOK_URL') ?? ''
const TOKI_EMAIL_WEBHOOK_API_KEY = Deno.env.get('TOKI_EMAIL_WEBHOOK_API_KEY') ?? ''

async function sendTokiBookingNotification(booking: Record<string, unknown>) {
  if (!TOKI_EMAIL_WEBHOOK_URL) {
    console.warn('TOKI Make webhook is not configured; booking remains saved.')
    return 'not_configured'
  }
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 8000)
  try {
    const result = await fetch(TOKI_EMAIL_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(TOKI_EMAIL_WEBHOOK_API_KEY ? { 'x-make-apikey': TOKI_EMAIL_WEBHOOK_API_KEY } : {}),
      },
      body: JSON.stringify({ kind: 'toki_booking_notification', booking }),
      signal: controller.signal,
    })
    // Make's default Custom Webhook response is HTTP 200 with plain-text "Accepted".
    // That confirms queue acceptance, not successful completion of later Gmail/Sheets modules.
    if (!result.ok) {
      console.warn('TOKI Make webhook rejected the booking notification:', result.status)
      return 'failed'
    }
    return 'queued'
  } catch (error) {
    console.warn('TOKI Make webhook request failed:', error instanceof Error ? error.name : 'unknown')
    return 'failed'
  } finally {
    clearTimeout(timeout)
  }
}

Deno.serve(async (request) => {
  const origin = request.headers.get('origin')

  // Safe deployment probe: reports configuration state, never key material.
  if (request.method === 'GET') {
    const ready = Boolean(SUPABASE_URL && SERVICE_ROLE_KEY && ALLOWED_ORIGIN && ALLOWED_HOSTNAME && RATE_SECRET)
    return response({ ok: ready, service: 'portfolio-submit', status: ready ? 'ready' : 'missing_server_credentials' }, ready ? 200 : 503, origin)
  }
  if (request.method === 'OPTIONS') return response({ ok: true }, 204, origin)
  if (request.method !== 'POST') return response({ ok: false, message: 'Method not allowed.' }, 405, origin)
  if (!SUPABASE_URL || !SERVICE_ROLE_KEY || !ALLOWED_ORIGIN || !RATE_SECRET) {
    return response({ ok: false, message: 'The portfolio submission service is not fully configured.' }, 503, origin)
  }
  if (!origin || origin !== ALLOWED_ORIGIN) return response({ ok: false, message: 'Origin not allowed.' }, 403, origin)
  const contentLength = Number(request.headers.get('content-length') ?? '0')
  if (contentLength > 12_000) return response({ ok: false, message: 'Request is too large.' }, 413, origin)

  let payload: Record<string, unknown>
  try {
    const rawBody = await readLimitedBody(request, 12_000)
    if (rawBody === null) return response({ ok: false, message: 'Request is too large.' }, 413, origin)
    const parsed: unknown = JSON.parse(rawBody)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return response({ ok: false, message: 'The request body must be a JSON object.' }, 400, origin)
    }
    payload = parsed as Record<string, unknown>
  } catch { return response({ ok: false, message: 'Invalid JSON body.' }, 400, origin) }
  const kind = String(payload.kind ?? '')
  if (!['inquiry', 'comment', 'page_view', 'toki_booking'].includes(kind)) return response({ ok: false, message: 'Unsupported submission type.' }, 400, origin)

  // Honeypot: respond successfully without storing anything so simple bots do not learn the trap.
  if (typeof payload.website === 'string' && payload.website.trim()) return response({ ok: true }, 200, origin)

  const forwarded = request.headers.get('cf-connecting-ip') ?? request.headers.get('x-real-ip') ?? request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'unavailable'
  // Only an HMAC digest reaches Postgres; the raw address is neither stored nor logged.
  const bucket = await hmacHex(RATE_SECRET, forwarded)
  const limits: Record<string, number> = { inquiry: 4, comment: 6, page_view: 60, toki_booking: 4 }
  try {
    const allowed = await consumeQuota(bucket, kind, limits[kind] ?? 4)
    if (!allowed) return response({ ok: false, message: 'Too many submissions from this network. Please try again later.' }, 429, origin)
  } catch (error) {
    console.error('Quota check failed:', error)
    return response({ ok: false, message: 'Submission protection is temporarily unavailable.' }, 503, origin)
  }

  if (kind !== 'page_view') {
    const token = typeof payload.turnstileToken === 'string' ? payload.turnstileToken : ''
    const expectedAction = kind === 'inquiry'
      ? 'portfolio_inquiry'
      : kind === 'comment'
        ? 'portfolio_comment'
        : 'toki_booking'
    const isTokiBooking = kind === 'toki_booking'
    const secret = isTokiBooking ? TOKI_TURNSTILE_SECRET : TURNSTILE_SECRET
    if (!(await verifyTurnstile(token, expectedAction, secret, isTokiBooking))) return response({ ok: false, message: 'Human verification failed. Please retry the challenge.' }, 400, origin)
  }

  try {
    if (kind === 'toki_booking') {
      const name = readText(payload.name)
      const contactMethod = readText(payload.contact_method)
      const contactValue = readText(payload.contact_value)
      const sessionType = readText(payload.session_type)
      const preferredDate = readText(payload.preferred_date)
      const alternateDate = readText(payload.alternate_date) || null
      const preferredTime = readText(payload.preferred_time)
      const location = readText(payload.location)
      const notes = readText(payload.notes)
      const participants = payload.participants
      const privacyConsent = payload.privacy_consent === true
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      const allowedContactMethods = ['instagram', 'facebook', 'email']
      const allowedSessions = [
        'Quick Snap', 'Toki Portraits', 'Signature Session',
        'Duo Session', 'Outdoor session', 'Event coverage', 'Custom session',
      ]
      const preferredTimePattern = /^(?:[01]\d|2[0-3]):[0-5]\d$/
      const today = manilaToday()
      const valid = name !== null && name.length >= 1 && name.length <= 100
        && contactMethod !== null && allowedContactMethods.includes(contactMethod)
        && contactValue !== null && contactValue.length >= 2 && contactValue.length <= 254
        && (contactMethod !== 'email' || emailPattern.test(contactValue))
        && sessionType !== null && allowedSessions.includes(sessionType)
        && preferredDate !== null && isValidDateOnly(preferredDate, today)
        && (!alternateDate || isValidDateOnly(alternateDate, today))
        && alternateDate !== preferredDate
        && preferredTime !== null && preferredTimePattern.test(preferredTime)
        && location !== null && location.length >= 2 && location.length <= 200
        && typeof participants === 'number' && Number.isInteger(participants) && participants >= 1 && participants <= 12
        && notes !== null && notes.length >= 10 && notes.length <= 2000
        && privacyConsent
      if (!valid) {
        return response({ ok: false, message: 'Please review your contact details, session, dates, exact requested time (24-hour HH:MM), location, participant count, and privacy confirmation.' }, 400, origin)
      }

      const referenceCode = `TOKI-${crypto.randomUUID().replaceAll('-', '').slice(0, 8).toUpperCase()}`
      const rows = await insertRecord('toki_booking_requests', {
        reference_code: referenceCode,
        name,
        contact_method: contactMethod,
        contact_value: contactValue,
        session_type: sessionType,
        preferred_date: preferredDate,
        alternate_date: alternateDate,
        preferred_time: preferredTime,
        location,
        participants,
        notes,
        privacy_consent: true,
        status: 'new',
      }, 'reference_code')
      const savedReference = Array.isArray(rows) ? readText(rows[0]?.reference_code) : null
      if (!savedReference) throw new Error('The request was saved but its reference could not be confirmed.')
      const notificationStatus = await sendTokiBookingNotification({
        reference_code: savedReference,
        name,
        contact_method: contactMethod,
        contact_value: contactValue,
        session_type: sessionType,
        preferred_date: preferredDate,
        alternate_date: alternateDate,
        preferred_time: preferredTime,
        location,
        participants,
        notes,
      })
      // Email is best-effort: a mail outage must never make a saved booking look unsaved.
      return response({ ok: true, reference_code: savedReference, notification_status: notificationStatus }, 200, origin)
    }

    if (kind === 'inquiry') {
      const name = readText(payload.name)
      const email = readText(payload.email)
      const subject = readText(payload.subject)
      const message = readText(payload.message)
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (name === null || email === null || subject === null || message === null
        || name.length < 1 || name.length > 100 || !emailPattern.test(email) || email.length > 254
        || subject.length < 1 || subject.length > 140 || message.length < 10 || message.length > 5000) {
        return response({ ok: false, message: 'Please check the name, email, subject, and message length.' }, 400, origin)
      }
      await insertRecord('inquiries', { name, email, subject, message, status: 'new' })
      return response({ ok: true }, 200, origin)
    }

    if (kind === 'comment') {
      const display_name = readText(payload.display_name)
      const body = readText(payload.body)
      if (display_name === null || body === null
        || display_name.length < 1 || display_name.length > 60 || body.length < 3 || body.length > 1000) {
        return response({ ok: false, message: 'Please check the display name and comment length.' }, 400, origin)
      }
      await insertRecord('comments', { display_name, body, status: 'pending' })
      return response({ ok: true }, 200, origin)
    }

    const session_id = readText(payload.session_id)
    const path = readText(payload.path)
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    if (session_id === null || path === null || !uuidPattern.test(session_id) || !/^\/[a-z0-9/_-]{0,99}$/i.test(path) || path.includes('//')) {
      return response({ ok: false, message: 'Invalid anonymous analytics event.' }, 400, origin)
    }
    await insertRecord('page_views', { session_id, path })
    return response({ ok: true }, 200, origin)
  } catch (error) {
    console.error('Portfolio submission failed:', error)
    return response({ ok: false, message: error instanceof Error ? error.message : 'Submission failed.' }, 500, origin)
  }
})
