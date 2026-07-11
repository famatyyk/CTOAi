import { beforeEach, describe, expect, it, vi } from "vitest"
import os from "node:os"
import path from "node:path"

const fetchWithTimeoutMock = vi.hoisted(() => vi.fn())
const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

vi.mock("@/lib/config", () => ({
  getServerApiUrl: () => "http://localhost:8000",
}))

vi.mock("@/lib/fetchWithTimeout", () => ({
  fetchWithTimeout: fetchWithTimeoutMock,
}))

describe("Control Center snapshot route", () => {
  beforeEach(() => {
    fetchWithTimeoutMock.mockReset()
    requireControlCenterReadAccessMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: true,
      viewer: { username: "operator", displayName: "Operator", role: "operator" },
    })
    process.env.CTOA_HELPER_CLIENT_STATE_PATH = path.join(os.tmpdir(), `ctoa-control-center-missing-${Date.now()}.json`)
  })

  it("requires operator access before collecting the snapshot", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue({
      ok: false,
      response: new Response(JSON.stringify({ ok: false, error: "denied" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    })
    const { GET } = await import("./route")

    const response = await GET()

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center snapshot")
    expect(fetchWithTimeoutMock).not.toHaveBeenCalled()
  })

  it("sanitizes backend probe error summaries before returning JSON", async () => {
    fetchWithTimeoutMock.mockRejectedValue(
      new Error(
        [
          "probe failed token=secret-token-value",
          "C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
          "/tmp/ctoa/control-center/status.json",
        ].join(" "),
      ),
    )
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.backend.reachable).toBe(false)
    expect(payload.backend.summary).toContain("token=[redacted]")
    expect(payload.backend.summary).toContain("[external]/client")
    expect(payload.backend.summary).toContain("[external]/status.json")
    expect(payload.backend.summary).not.toContain("secret-token-value")
    expect(payload.backend.summary).not.toContain("C:\\Users\\zycie")
    expect(payload.backend.summary).not.toContain("/tmp/ctoa")
    expect(payload.operational.sourceStates.some((source: { status: string }) => source.status === "source_blocked")).toBe(true)
    expect(payload.operational.clientStates[0].status).toBe("unknown_build")
    expect(payload.operational.clientStates[0].safeFallback).toBe(true)
    expect(payload.operational.clientStates[0].evidenceStatus).toBe("stale_snapshot")
  })
})
