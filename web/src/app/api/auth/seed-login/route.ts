import { NextRequest, NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

const API_URL = getServerApiUrl()

const LOCAL_SEED_PASSWORDS: Record<string, string> = {
  famatyyk: "ctoa-owner",
  strategos: "ctoa-ops",
  recruit: "ctoa-community",
}

function isLocalHost(req: NextRequest): boolean {
  const host = req.nextUrl.hostname
  return process.env.NODE_ENV === "development" && (host === "localhost" || host === "127.0.0.1" || host === "::1")
}

export async function POST(req: NextRequest) {
  if (!isLocalHost(req)) {
    return NextResponse.json({ error: "Seed login is only available on localhost." }, { status: 403 })
  }

  const body = (await req.json().catch(() => ({}))) as { username?: string }
  const username = body.username?.trim().toLowerCase()
  const password = username ? LOCAL_SEED_PASSWORDS[username] : undefined

  if (!username || !password) {
    return NextResponse.json({ error: "Unknown seed account." }, { status: 400 })
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
  const { token: _token, ...safeData } = data as { token?: string; [key: string]: unknown }
  const result = NextResponse.json(safeData, { status: response.status })

  if (response.ok && _token) {
    result.cookies.set("ctoa_token", _token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 })
  }

  return result
}
