import { NextRequest } from "next/server"
import { afterEach, describe, expect, it, vi } from "vitest"

function chatRequest(headers: HeadersInit) {
  return new NextRequest("http://localhost/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify({ messages: [{ role: "user", content: "status" }] }),
  })
}

describe("chat route origin guard", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("rejects cross-site POST requests before backend chat forwarding", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
    const { POST } = await import("./route")

    const response = await POST(chatRequest({ Origin: "https://attacker.example" }))
    const payload = await response.json()

    expect(response.status).toBe(403)
    expect(payload.code).toBe("CROSS_SITE_REQUEST")
    expect(payload.detail).toMatch(/Cross-site chat/)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it("validates same-origin Origin and cross-site fetch metadata", async () => {
    const { validateChatRequestOrigin } = await import("./route")

    expect(validateChatRequestOrigin(chatRequest({ Origin: "http://localhost" }))).toEqual({ ok: true })
    expect(validateChatRequestOrigin(chatRequest({ "Sec-Fetch-Site": "cross-site" }))).toEqual({
      ok: false,
      error: "Cross-site chat requests are not allowed.",
    })
  })
})
