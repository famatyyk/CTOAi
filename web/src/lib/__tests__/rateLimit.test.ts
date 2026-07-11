import { afterEach, describe, expect, it, vi } from "vitest"
import { createIpRateLimiter, getClientIp, trustProxyHeaders } from "../rateLimit"

describe("rateLimit", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("allows requests until the limit is reached", () => {
    const consume = createIpRateLimiter(2, 60_000)

    expect(consume("1.2.3.4").allowed).toBe(true)
    expect(consume("1.2.3.4").allowed).toBe(true)
    expect(consume("1.2.3.4").allowed).toBe(false)
  })

  it("resets the window after expiry", () => {
    vi.useFakeTimers()
    try {
      const consume = createIpRateLimiter(1, 1000)
      expect(consume("1.2.3.4").allowed).toBe(true)
      expect(consume("1.2.3.4").allowed).toBe(false)
      vi.advanceTimersByTime(1001)
      expect(consume("1.2.3.4").allowed).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })

  it("ignores forwarded IP headers by default", () => {
    const req = new Request("https://example.test", {
      headers: {
        "x-forwarded-for": "203.0.113.7, 10.0.0.1",
        "x-real-ip": "203.0.113.8",
      },
    })

    expect(trustProxyHeaders()).toBe(false)
    expect(getClientIp(req as never)).toBe("unknown")
  })

  it("extracts the first forwarded IP only when proxy headers are trusted", () => {
    vi.stubEnv("CTOA_TRUST_PROXY_HEADERS", "true")
    const req = new Request("https://example.test", {
      headers: { "x-forwarded-for": "203.0.113.7, 10.0.0.1" },
    })

    expect(getClientIp(req as never)).toBe("203.0.113.7")
  })

  it("falls back to a valid real IP only when forwarded IP is invalid", () => {
    vi.stubEnv("CTOA_TRUST_PROXY_HEADERS", "1")
    const req = new Request("https://example.test", {
      headers: {
        "x-forwarded-for": "not-an-ip, 203.0.113.7",
        "x-real-ip": "203.0.113.8",
      },
    })

    expect(getClientIp(req as never)).toBe("203.0.113.8")
  })

  it("rejects invalid trusted proxy header values", () => {
    vi.stubEnv("CTOA_TRUST_PROXY_HEADERS", "yes")
    const req = new Request("https://example.test", {
      headers: {
        "x-forwarded-for": "203.0.113.7:1234",
        "x-real-ip": "bad-real-ip",
      },
    })

    expect(getClientIp(req as never)).toBe("unknown")
  })
})
