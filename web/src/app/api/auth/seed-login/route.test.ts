import { readFile } from "node:fs/promises"
import path from "node:path"
import { NextRequest } from "next/server"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const fetchWithTimeoutMock = vi.hoisted(() => vi.fn())

vi.mock("@/lib/config", () => ({
  getServerApiUrl: () => "http://ctoa-api.test",
}))

vi.mock("@/lib/fetchWithTimeout", () => ({
  fetchWithTimeout: fetchWithTimeoutMock,
}))

function seedRequest(username = "recruit", url = "http://localhost/api/auth/seed-login", headers: HeadersInit = {}) {
  return new NextRequest(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ username }),
  })
}

describe("local seed-login route", () => {
  const originalEnv = { ...process.env }

  beforeEach(() => {
    vi.resetModules()
    fetchWithTimeoutMock.mockReset()
    process.env = { ...originalEnv }
    delete process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN
    delete process.env.CTOA_SEED_RECRUIT_PASSWORD
    delete process.env.CTOA_SEED_STRATEGOS_PASSWORD
    delete process.env.CTOA_SEED_FAMATYYK_PASSWORD
  })

  afterEach(() => {
    process.env = { ...originalEnv }
  })

  it("keeps legacy seed passwords out of the route source", async () => {
    const source = await readFile(path.join(process.cwd(), "src/app/api/auth/seed-login/route.ts"), "utf-8")

    expect(source).not.toContain("ctoa-owner")
    expect(source).not.toContain("ctoa-ops")
    expect(source).not.toContain("ctoa-community")
  })

  it("is disabled by default even on localhost", async () => {
    process.env.CTOA_SEED_RECRUIT_PASSWORD = "local-only-password"
    const { POST } = await import("./route")

    const response = await POST(seedRequest())

    expect(response.status).toBe(403)
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })

  it("uses only explicit local env credentials when enabled", async () => {
    process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN = "true"
    process.env.CTOA_SEED_RECRUIT_PASSWORD = "local-only-password"
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(JSON.stringify({ token: "secret-token", user: { username: "recruit" } }), { status: 200 }),
    )
    const { POST } = await import("./route")

    const response = await POST(seedRequest())
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload).toEqual({ user: { username: "recruit" } })
    expect(fetchWithTimeoutMock).toHaveBeenCalledWith(
      "http://ctoa-api.test/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "recruit", password: "local-only-password" }),
      }),
      5000,
    )
  })

  it("strips nested backend tokens and sanitizes seed-login response strings", async () => {
    process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN = "true"
    process.env.CTOA_SEED_RECRUIT_PASSWORD = "local-only-password"
    fetchWithTimeoutMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          token: "cookie-token-value",
          refresh_token: "refresh-token-value",
          user: {
            username: "recruit",
            auth_token: "nested-token-value",
          },
          detail: "seed token=secret-token-value /home/runner/work/CTOAi/private-output.json",
        }),
        { status: 200 },
      ),
    )
    const { POST } = await import("./route")

    const response = await POST(seedRequest())
    const payload = await response.json()
    const setCookie = response.headers.get("set-cookie") || ""

    expect(response.status).toBe(200)
    expect(setCookie).toContain("ctoa_token=cookie-token-value")
    expect(payload).toEqual({
      user: { username: "recruit" },
      detail: "seed token=[redacted] [external]/private-output.json",
    })
    expect(JSON.stringify(payload)).not.toContain("cookie-token-value")
    expect(JSON.stringify(payload)).not.toContain("refresh-token-value")
    expect(JSON.stringify(payload)).not.toContain("nested-token-value")
    expect(JSON.stringify(payload)).not.toContain("secret-token-value")
    expect(JSON.stringify(payload)).not.toContain("/home/runner")
  })

  it("rejects cross-site local seed-login before backend forwarding", async () => {
    process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN = "true"
    process.env.CTOA_SEED_RECRUIT_PASSWORD = "local-only-password"
    const { POST } = await import("./route")

    const response = await POST(seedRequest("recruit", "http://localhost/api/auth/seed-login", { Origin: "https://attacker.example" }))
    const payload = await response.json()

    expect(response.status).toBe(403)
    expect(payload.error).toMatch(/Cross-site local seed-login/)
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })

  it("rejects production even when the local opt-in flag is set", async () => {
    ;(process.env as Record<string, string | undefined>).NODE_ENV = "production"
    process.env.CTOA_ENABLE_LOCAL_SEED_LOGIN = "true"
    process.env.CTOA_SEED_RECRUIT_PASSWORD = "local-only-password"
    const { POST } = await import("./route")

    const response = await POST(seedRequest())

    expect(response.status).toBe(403)
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })
})
