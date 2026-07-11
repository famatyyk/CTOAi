import { beforeEach, describe, expect, it, vi } from "vitest"
import os from "node:os"
import path from "node:path"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

describe("/api/clients/:id/capabilities", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: true,
      viewer: { username: "operator", displayName: "Operator", role: "operator" },
    })
  })

  it("requires operator access before reading client capabilities", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: false,
      response: new Response(JSON.stringify({ ok: false, error: "denied" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    })
    const { GET } = await import("./route")

    const response = await GET(new Request("http://localhost/api/clients/otc-local-default/capabilities"), {
      params: Promise.resolve({ id: "otc-local-default" }),
    })

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center client capabilities")
  })

  it("returns safe fallback capabilities for the local OTC client", async () => {
    process.env.CTOA_HELPER_CLIENT_STATE_PATH = path.join(os.tmpdir(), `ctoa-route-missing-${Date.now()}.json`)
    const { GET } = await import("./route")
    const response = await GET(new Request("http://localhost/api/clients/otc-local-default/capabilities"), {
      params: Promise.resolve({ id: "otc-local-default" }),
    })
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.status).toBe("unknown_build")
    expect(payload.safe_fallback).toBe(true)
    expect(payload.report_error).toBe("missing")
  })

  it("returns 404 for unknown clients", async () => {
    const { GET } = await import("./route")
    const response = await GET(new Request("http://localhost/api/clients/missing/capabilities"), {
      params: Promise.resolve({ id: "missing" }),
    })
    const payload = await response.json()

    expect(response.status).toBe(404)
    expect(payload.error).toBe("client_not_found")
  })
})
