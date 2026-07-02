import { describe, expect, it, vi } from "vitest"
import { createIpRateLimiter, getClientIp } from "../rateLimit"

describe("rateLimit", () => {
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

  it("extracts the first forwarded IP", () => {
    const req = new Request("https://example.test", {
      headers: { "x-forwarded-for": "203.0.113.7, 10.0.0.1" },
    })

    expect(getClientIp(req as never)).toBe("203.0.113.7")
  })
})
