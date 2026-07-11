import { NextRequest } from "next/server"
import { afterEach, describe, expect, it, vi } from "vitest"

const fetchWithTimeoutMock = vi.hoisted(() => vi.fn())

vi.mock("@/lib/fetchWithTimeout", () => ({
  fetchWithTimeout: fetchWithTimeoutMock,
}))

function authRequest(headers: HeadersInit, body: Record<string, unknown> = { action: "setRole", payload: { username: "operator", role: "owner" } }) {
  return new NextRequest("http://localhost/api/auth", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  })
}

describe("auth route origin guard", () => {
  afterEach(() => {
    fetchWithTimeoutMock.mockReset()
    vi.unstubAllEnvs()
  })

  it("rejects cross-site POST requests before backend auth forwarding", async () => {
    const { POST } = await import("./route")

    const response = await POST(authRequest({ Origin: "https://attacker.example" }))
    const payload = await response.json()

    expect(response.status).toBe(403)
    expect(payload.error).toMatch(/Cross-site auth/)
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })

  it("rejects cross-site fetch metadata before parsing action forwarding", async () => {
    const { POST } = await import("./route")

    const response = await POST(authRequest({ "Sec-Fetch-Site": "cross-site" }))

    expect(response.status).toBe(403)
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })

  it("validates same-origin Origin and Referer headers", async () => {
    const { validateAuthRequestOrigin } = await import("./route")

    expect(validateAuthRequestOrigin(authRequest({ Origin: "http://localhost" }))).toEqual({ ok: true })
    expect(validateAuthRequestOrigin(authRequest({ Referer: "http://localhost/control-center" }))).toEqual({
      ok: true,
    })
    expect(validateAuthRequestOrigin(authRequest({ Referer: "https://attacker.example/x" }))).toEqual({
      ok: false,
      error: "Cross-site auth requests are not allowed.",
    })
  })

  it("sets Secure on ctoa token cookies in production", async () => {
    vi.stubEnv("NODE_ENV", "production")
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(JSON.stringify({ token: "secure-token", user: { username: "operator" } }), { status: 200 }),
    )
    const { POST } = await import("./route")

    const response = await POST(
      authRequest(
        { Origin: "http://localhost" },
        { action: "login", payload: { username: "operator", password: "local-password" } },
      ),
    )
    const payload = await response.json()
    const setCookie = response.headers.get("set-cookie") || ""

    expect(response.status).toBe(200)
    expect(payload).toEqual({ user: { username: "operator" } })
    expect(JSON.stringify(payload)).not.toContain("secure-token")
    expect(setCookie).toContain("ctoa_token=secure-token")
    expect(setCookie).toContain("HttpOnly")
    expect(setCookie).toContain("Secure")
    expect(setCookie.toLowerCase()).toContain("samesite=lax")
  })

  it("strips token-like backend auth fields from browser-visible JSON", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          token: "secret-token-value",
          access_token: "json-token-value",
          refresh_token: "refresh-token-value",
          user: {
            username: "operator",
            auth_token: "nested-token-value",
          },
        }),
        { status: 200 },
      ),
    )
    const { POST } = await import("./route")

    const response = await POST(
      authRequest(
        { Origin: "http://localhost" },
        { action: "login", payload: { username: "operator", password: "local-password" } },
      ),
    )
    const payload = await response.json()
    const setCookie = response.headers.get("set-cookie") || ""

    expect(response.status).toBe(200)
    expect(setCookie).toContain("ctoa_token=secret-token-value")
    expect(payload).toEqual({ user: { username: "operator" } })
    expect(JSON.stringify(payload)).not.toContain("secret-token-value")
    expect(JSON.stringify(payload)).not.toContain("json-token-value")
    expect(JSON.stringify(payload)).not.toContain("refresh-token-value")
    expect(JSON.stringify(payload)).not.toContain("nested-token-value")
  })

  it("sanitizes backend auth error payloads before returning JSON", async () => {
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            "invite failed token=secret-token-value",
            "C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
            "/home/runner/work/CTOAi/private-output.json",
          ].join(" "),
          token: "backend-token-value",
        }),
        { status: 400 },
      ),
    )
    const { POST } = await import("./route")

    const response = await POST(
      authRequest(
        { Origin: "http://localhost" },
        { action: "login", payload: { username: "operator", password: "local-password" } },
      ),
    )
    const payload = await response.json()

    expect(response.status).toBe(400)
    expect(payload.detail).toContain("token=[redacted]")
    expect(payload.detail).toContain("[external]/client")
    expect(payload.detail).toContain("[external]/private-output.json")
    expect(JSON.stringify(payload)).not.toContain("secret-token-value")
    expect(JSON.stringify(payload)).not.toContain("backend-token-value")
    expect(JSON.stringify(payload)).not.toContain("C:\\Users\\zycie")
    expect(JSON.stringify(payload)).not.toContain("/home/runner")
  })
})
