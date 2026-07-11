import { NextRequest, NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"
import { validateSameOriginRequest } from "@/lib/requestOriginGuard"
import { CTOA_TOKEN_COOKIE_NAME, ctoaTokenCookieOptions } from "@/lib/authCookies"
import { authProxyCookieToken, sanitizeAuthProxyPayload } from "@/lib/authProxySanitizer"

const API_URL = getServerApiUrl()

const LOCAL_SEED_PASSWORD_ENV: Record<string, string> = {
  famatyyk: "CTOA_SEED_FAMATYYK_PASSWORD",
  strategos: "CTOA_SEED_STRATEGOS_PASSWORD",
  recruit: "CTOA_SEED_RECRUIT_PASSWORD",
}

function isLocalSeedLoginAllowed(req: NextRequest): boolean {
  const host = req.nextUrl.hostname
  const localHost = host === "localhost" || host === "127.0.0.1" || host === "::1"
  const enabled = process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN === "true"
  const nonProduction = process.env.NODE_ENV !== "production"
  return enabled && nonProduction && localHost
}

function localSeedPassword(username: string): string {
  const envName = LOCAL_SEED_PASSWORD_ENV[username]
  return envName ? process.env[envName]?.trim() || "" : ""
}

export function validateSeedLoginRequestOrigin(request: Request) {
  return validateSameOriginRequest(request, { requestLabel: "local seed-login" })
}

export async function POST(req: NextRequest) {
  const originGate = validateSeedLoginRequestOrigin(req)
  if (!originGate.ok) {
    return NextResponse.json({ error: originGate.error }, { status: 403 })
  }

  if (!isLocalSeedLoginAllowed(req)) {
    return NextResponse.json(
      { error: "Local seed login is disabled. Enable it only for local development with CTOA_ENABLE_LOCAL_SEED_LOGIN=true." },
      { status: 403 },
    )
  }

  const body = (await req.json().catch(() => ({}))) as { username?: string }
  const username = body.username?.trim().toLowerCase()
  const password = username ? localSeedPassword(username) : ""

  if (!username || !password) {
    return NextResponse.json({ error: "Unknown or unconfigured local seed account." }, { status: 400 })
  }

  const response = await fetchWithTimeout(
    API_URL + "/api/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    },
    5000,
  )
  const data = await response.json().catch(() => ({}))
  const cookieToken = authProxyCookieToken(data)
  const result = NextResponse.json(sanitizeAuthProxyPayload(data), { status: response.status })

  if (response.ok && cookieToken) {
    result.cookies.set(CTOA_TOKEN_COOKIE_NAME, cookieToken, ctoaTokenCookieOptions())
  }

  return result
}
