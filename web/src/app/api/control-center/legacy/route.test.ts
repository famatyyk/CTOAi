import { beforeEach, describe, expect, it, vi } from "vitest"

const fetchWithTimeoutMock = vi.hoisted(() => vi.fn())

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: () => ({ value: "session-token" }),
  }),
}))

vi.mock("@/lib/config", () => ({
  getServerApiUrl: () => "http://localhost:8000",
}))

vi.mock("@/lib/fetchWithTimeout", () => ({
  fetchWithTimeout: fetchWithTimeoutMock,
}))

describe("Control Center legacy route", () => {
  beforeEach(() => {
    fetchWithTimeoutMock.mockReset()
  })

  it("sanitizes backend fetch error details before returning JSON", async () => {
    fetchWithTimeoutMock.mockRejectedValue(
      new Error(
        [
          "legacy backend failed Bearer abcdefghijklmnopqrstuvwxyz",
          "password=legacy-password-value",
          "/home/runner/work/CTOAi/private-output.json",
        ].join(" "),
      ),
    )
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.capabilities.dashboard.status).toBe(503)
    expect(payload.capabilities.dashboard.body.detail).toContain("Bearer [redacted]")
    expect(payload.capabilities.dashboard.body.detail).toContain("password=[redacted]")
    expect(payload.capabilities.dashboard.body.detail).toContain("[external]/private-output.json")
    expect(payload.capabilities.dashboard.body.detail).not.toContain("abcdefghijklmnopqrstuvwxyz")
    expect(payload.capabilities.dashboard.body.detail).not.toContain("legacy-password-value")
    expect(payload.capabilities.dashboard.body.detail).not.toContain("/home/runner")
  })
})
