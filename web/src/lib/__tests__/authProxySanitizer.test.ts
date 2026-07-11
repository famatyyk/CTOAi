import { afterEach, describe, expect, it, vi } from "vitest"
import { authProxyCookieToken, sanitizeAuthProxyPayload } from "../authProxySanitizer"

describe("auth proxy sanitizer", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("keeps cookie token extraction separate from browser-visible payloads", () => {
    vi.stubEnv("CTOA_REPO_ROOT", "C:\\repo\\CTOAi")

    const raw = {
      token: "cookie-token-value",
      refresh_token: "refresh-token-value",
      user: {
        username: "operator",
        auth_token: "nested-token-value",
        note: "profile at C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
      },
      detail: "failed token=secret-token-value /tmp/ctoa/auth/result.json",
    }

    const sanitized = sanitizeAuthProxyPayload(raw)

    expect(authProxyCookieToken(raw)).toBe("cookie-token-value")
    expect(sanitized).toEqual({
      user: {
        username: "operator",
        note: "profile at [external]/client",
      },
      detail: "failed token=[redacted] [external]/result.json",
    })
    expect(JSON.stringify(sanitized)).not.toContain("cookie-token-value")
    expect(JSON.stringify(sanitized)).not.toContain("refresh-token-value")
    expect(JSON.stringify(sanitized)).not.toContain("nested-token-value")
    expect(JSON.stringify(sanitized)).not.toContain("secret-token-value")
    expect(JSON.stringify(sanitized)).not.toContain("C:\\Users\\zycie")
    expect(JSON.stringify(sanitized)).not.toContain("/tmp/ctoa")
  })
})
