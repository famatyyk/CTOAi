import { beforeEach, describe, expect, it, vi } from "vitest"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())
const getClientsMock = vi.hoisted(() => vi.fn())
const getTelemetryEventsMock = vi.hoisted(() => vi.fn())
const getLatestUpdatesMock = vi.hoisted(() => vi.fn())
const getDiffLedgerMock = vi.hoisted(() => vi.fn())
const validateConfigDryRunMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

vi.mock("@/lib/tibiaOperationalState", () => ({
  getClients: getClientsMock,
  getTelemetryEvents: getTelemetryEventsMock,
  getLatestUpdates: getLatestUpdatesMock,
  getDiffLedger: getDiffLedgerMock,
  validateConfigDryRun: validateConfigDryRunMock,
}))

function denyAccess() {
  return {
    ok: false,
    response: new Response(JSON.stringify({ ok: false, error: "denied" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    }),
  }
}

describe("Control Center operational route access", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess())
    getClientsMock.mockReset()
    getTelemetryEventsMock.mockReset()
    getLatestUpdatesMock.mockReset()
    getDiffLedgerMock.mockReset()
    validateConfigDryRunMock.mockReset()
  })

  it("denies client inventory before collecting local state", async () => {
    const { GET } = await import("../clients/route")
    const response = await GET()

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center client inventory")
    expect(getClientsMock).not.toHaveBeenCalled()
  })

  it("denies telemetry events before collecting local state", async () => {
    const { GET } = await import("../events/route")
    const response = await GET()

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center telemetry events")
    expect(getTelemetryEventsMock).not.toHaveBeenCalled()
  })

  it("denies latest updates before collecting local state", async () => {
    const { GET } = await import("../updates/latest/route")
    const response = await GET()

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center latest updates")
    expect(getLatestUpdatesMock).not.toHaveBeenCalled()
  })

  it("denies diff ledgers before resolving the requested surface", async () => {
    const { GET } = await import("../diffs/[surface]/route")
    const response = await GET(new Request("http://localhost/api/diffs/helper"), {
      params: Promise.resolve({ surface: "helper" }),
    })

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center diff ledger")
    expect(getDiffLedgerMock).not.toHaveBeenCalled()
  })

  it("denies configuration dry runs before parsing or validating input", async () => {
    const { POST } = await import("../config/validate-dry-run/route")
    const response = await POST(
      new Request("http://localhost/api/config/validate-dry-run", {
        method: "POST",
        body: JSON.stringify({ client_id: "otc-local-default" }),
        headers: { "Content-Type": "application/json" },
      }),
    )

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center configuration dry run")
    expect(validateConfigDryRunMock).not.toHaveBeenCalled()
  })
})
