import { NextRequest } from "next/server"

type RateWindow = {
  count: number
  resetAt: number
}

export function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for")
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim()
    if (first) return first
  }

  const real = req.headers.get("x-real-ip")?.trim()
  return real || "unknown"
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
