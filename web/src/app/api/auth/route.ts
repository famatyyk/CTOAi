import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

const API_URL = process.env.VPS_API_URL ?? "http://116.202.96.250:8001"
const AUTH_RATE_LIMIT_PER_MIN = 20
const AUTH_RATE_WINDOW_MS = 60_000

type RateWindow = {
  count: number
  resetAt: number
}

const authIpWindows = new Map<string, RateWindow>()


function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for")
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim()
    if (first) return first
  }
  const real = req.headers.get("x-real-ip")?.trim()
  return real || "unknown"
}

function consumeRateWindow(ip: string): { allowed: boolean; retryAfter: number } {
  const now = Date.now()
  const current = authIpWindows.get(ip)
  if (!current || current.resetAt <= now) {
    authIpWindows.set(ip, { count: 1, resetAt: now + AUTH_RATE_WINDOW_MS })
    return { allowed: true, retryAfter: 0 }
  }

  if (current.count >= AUTH_RATE_LIMIT_PER_MIN) {
    return { allowed: false, retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)) }
  }

  current.count += 1
  authIpWindows.set(ip, current)
  return { allowed: true, retryAfter: 0 }
}
async function backendFetch(path: string, init?: RequestInit) {
  const token = (await cookies()).get("ctoa_token")?.value
  return fetch(API_URL + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  })
}

export async function GET(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path") || "members"
  const map: Record<string, string> = {
    me: "/api/auth/me",
    members: "/api/community/members",
    feed: "/api/community/feed",
    invites: "/api/community/invites",
  }
  const target = map[path]
  if (!target) return NextResponse.json({ error: "Unsupported path" }, { status: 400 })

  try {
    const r = await backendFetch(target)
    const data = await r.json()
    return NextResponse.json(data, { status: r.status })
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 })
  }
}

export async function POST(req: NextRequest) {
  const ip = getClientIp(req)
  const gate = consumeRateWindow(ip)
  if (!gate.allowed) {
    return NextResponse.json(
      {
        detail: "Rate limit exceeded. Please retry shortly.",
        code: "RATE_LIMITED",
        retry_after: gate.retryAfter,
      },
      { status: 429, headers: { "Retry-After": String(gate.retryAfter) } },
    )
  }
  const body = await req.json()
  const action = body?.action

  try {
    if (action === "register") {
      const r = await fetch(API_URL + "/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body.payload || {}),
      })
      const data = await r.json()
      const response = NextResponse.json(data, { status: r.status })
      if (r.ok && data?.token) {
        response.cookies.set("ctoa_token", data.token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 })
      }
      return response
    }

    if (action === "login") {
      const r = await fetch(API_URL + "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body.payload || {}),
      })
      const data = await r.json()
      const response = NextResponse.json(data, { status: r.status })
      if (r.ok && data?.token) {
        response.cookies.set("ctoa_token", data.token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 })
      }
      return response
    }

    if (action === "logout") {
      const response = NextResponse.json({ ok: true })
      response.cookies.set("ctoa_token", "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 })
      return response
    }

    if (action === "invite") {
      const r = await backendFetch("/api/community/invite", {
        method: "POST",
        body: JSON.stringify(body.payload || {}),
      })
      const data = await r.json()
      return NextResponse.json(data, { status: r.status })
    }

    if (action === "acceptInvite") {
      const r = await backendFetch("/api/community/invite/accept", {
        method: "POST",
        body: JSON.stringify(body.payload || {}),
      })
      const data = await r.json()
      const response = NextResponse.json(data, { status: r.status })
      if (r.ok && data?.token) {
        response.cookies.set("ctoa_token", data.token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 })
      }
      return response
    }

    if (action === "setRole") {
      const username = body?.payload?.username
      const role = body?.payload?.role
      if (!username || !role) return NextResponse.json({ error: "Missing username or role" }, { status: 400 })
      const r = await backendFetch(`/api/community/members/${encodeURIComponent(username)}/role`, {
        method: "POST",
        body: JSON.stringify({ role }),
      })
      const data = await r.json()
      return NextResponse.json(data, { status: r.status })
    }

    return NextResponse.json({ error: "Unsupported action" }, { status: 400 })
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 })
  }
}
