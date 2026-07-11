import { NextRequest } from "next/server"
import { isIP } from "node:net"

type RateWindow = {
  count: number
  resetAt: number
}

export function getClientIp(req: NextRequest): string {
  if (!trustProxyHeaders()) {
    return "unknown"
  }

  const forwarded = req.headers.get("x-forwarded-for")
  if (forwarded) {
    const first = normalizeIp(forwarded.split(",")[0])
    if (first) return first
  }

  const real = normalizeIp(req.headers.get("x-real-ip"))
  return real || "unknown"
}

export function trustProxyHeaders(): boolean {
  const value = (process.env.CTOA_TRUST_PROXY_HEADERS || "").trim().toLowerCase()
  return value === "1" || value === "true" || value === "yes" || value === "on"
}

function normalizeIp(value: string | null | undefined): string {
  const candidate = (value || "").trim()
  return isIP(candidate) ? candidate : ""
}

export function createIpRateLimiter(limit: number, windowMs: number) {
  const windows = new Map<string, RateWindow>()

  return function consume(ip: string): { allowed: boolean; retryAfter: number } {
    const now = Date.now()
    const current = windows.get(ip)

    if (!current || current.resetAt <= now) {
      windows.set(ip, { count: 1, resetAt: now + windowMs })
      return { allowed: true, retryAfter: 0 }
    }

    if (current.count >= limit) {
      return { allowed: false, retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)) }
    }

    current.count += 1
    windows.set(ip, current)
    return { allowed: true, retryAfter: 0 }
  }
}
