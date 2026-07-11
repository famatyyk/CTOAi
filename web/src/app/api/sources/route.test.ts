import { beforeEach, describe, expect, it, vi } from "vitest"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

describe("/api/sources", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: true,
      viewer: { username: "operator", displayName: "Operator", role: "operator" },
    })
  })

  it("requires operator access before reading the source inventory", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: false,
      response: new Response(JSON.stringify({ ok: false, error: "denied" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    })
    const { GET } = await import("./route")

    const response = await GET()

    expect(response.status).toBe(403)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center source inventory")
  })

  it("returns the Tibia source inventory contract", async () => {
    const { GET } = await import("./route")
    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.sources[0].source_kind).toBe("news")
    expect(payload.sources[0].status).toBe("source_blocked")
  })
})
