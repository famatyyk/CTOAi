import { beforeEach, describe, expect, it, vi } from "vitest"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())
const listControlCenterActionCapabilitiesMock = vi.hoisted(() => vi.fn())
const runControlCenterActionMock = vi.hoisted(() => vi.fn())
const projectControlCenterActionResultMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

vi.mock("@/lib/controlCenterActions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/controlCenterActions")>("@/lib/controlCenterActions")
  return {
    ...actual,
    listControlCenterActionCapabilities: listControlCenterActionCapabilitiesMock,
    runControlCenterAction: runControlCenterActionMock,
    projectControlCenterActionResult: projectControlCenterActionResultMock,
  }
})

const operator = { username: "operator", displayName: "Operator", role: "operator" as const }

function allowAccess() {
  return { ok: true as const, viewer: operator }
}

function denyAccess(status = 401) {
  return {
    ok: false as const,
    response: new Response(JSON.stringify({ ok: false, error: "Authentication required." }), { status }),
  }
}

function actionRequest(headers: HeadersInit, body: Record<string, unknown> = { actionId: "evidence-pack-refresh", dryRun: true }) {
  return new Request("http://localhost/api/control-center/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  })
}

describe("control center action capability route", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    listControlCenterActionCapabilitiesMock.mockReset()
    runControlCenterActionMock.mockReset()
    projectControlCenterActionResultMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue(allowAccess())
    listControlCenterActionCapabilitiesMock.mockResolvedValue({
      schemaVersion: 2,
      generatedAt: "2026-07-21T12:00:00.000Z",
      capabilities: [
        {
          id: "evidence-pack-refresh",
          label: "Rebuild evidence pack",
          description: "Refresh bounded evidence.",
          target: "local",
          riskClass: "safe_write",
          minimumRole: "operator",
          confirmationText: "refresh evidence pack",
          requiresReason: true,
          dryRunAvailable: true,
          enabled: true,
          executionMode: "dry_run_first",
          nativeDryRun: false,
          effect: "Refreshes bounded evidence.",
          evidence: "Records an audit.",
          preflight: {
            schemaVersion: 2,
            status: "ready",
            dryRunAllowed: true,
            executeAllowed: false,
            checks: [],
            blockers: [],
          },
        },
      ],
    })
  })

  it("requires read access before returning capability metadata", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess())
    const { GET } = await import("./route")
    const response = await GET()

    expect(response.status).toBe(401)
    expect(listControlCenterActionCapabilitiesMock).not.toHaveBeenCalled()
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center action capabilities")
  })

  it("returns schema-v2 capability metadata with private no-store cache headers", async () => {
    const { GET } = await import("./route")
    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(response.headers.get("Cache-Control")).toBe("private, no-store")
    expect(payload.schemaVersion).toBe(2)
    expect(JSON.stringify(payload)).not.toContain("commandSummary")
    expect(JSON.stringify(payload)).not.toContain("scripts/ops")
    expect(listControlCenterActionCapabilitiesMock).toHaveBeenCalledWith({ actor: operator })
  })

  it("rejects cross-site POST requests before action execution", async () => {
    const { POST } = await import("./route")
    const response = await POST(actionRequest({ Origin: "https://attacker.example" }))

    expect(response.status).toBe(403)
    expect(runControlCenterActionMock).not.toHaveBeenCalled()
    expect(requireControlCenterReadAccessMock).not.toHaveBeenCalled()
  })

  it("validates same-origin Origin and Referer headers", async () => {
    const { validateControlCenterActionRequestOrigin } = await import("./route")
    expect(validateControlCenterActionRequestOrigin(actionRequest({ Origin: "http://localhost" }))).toEqual({ ok: true })
    expect(validateControlCenterActionRequestOrigin(actionRequest({ Referer: "https://attacker.example/x" }))).toEqual({
      ok: false,
      error: "Cross-site Control Center action requests are not allowed.",
    })
  })

  it("passes only validated execution-gate fields to the server action engine", async () => {
    const internalResult = {
      action: { id: "evidence-pack-refresh" },
      dryRun: true,
      ok: true,
      output: "private output",
      auditId: "audit-1",
      completedAt: "2026-07-21T12:00:00.000Z",
      proofId: "proof-1",
      preflight: { schemaVersion: 2, status: "ready", dryRunAllowed: true, executeAllowed: true, checks: [], blockers: [] },
    }
    runControlCenterActionMock.mockResolvedValue(internalResult)
    projectControlCenterActionResultMock.mockReturnValue({
      schemaVersion: 2,
      actionId: "evidence-pack-refresh",
      dryRun: true,
      ok: true,
      status: "dry_run_validated",
      auditId: "audit-1",
      completedAt: "2026-07-21T12:00:00.000Z",
      proofId: "proof-1",
      preflight: internalResult.preflight,
      message: "Dry-run validation completed.",
    })
    const { POST } = await import("./route")
    const response = await POST(
      actionRequest(
        { Origin: "http://localhost" },
        { actionId: "evidence-pack-refresh", dryRun: true, proofId: "ignored-for-dry-run", reason: "ignored" },
      ),
    )
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(runControlCenterActionMock).toHaveBeenCalledWith({
      actionId: "evidence-pack-refresh",
      dryRun: true,
      proofId: "ignored-for-dry-run",
      reason: "ignored",
      confirmation: undefined,
      actor: operator,
    })
    expect(JSON.stringify(payload)).not.toContain("private output")
  })

  it("returns a bounded preflight response without executing when the gate is blocked", async () => {
    const { ControlCenterPreflightError } = await import("@/lib/controlCenterActions")
    runControlCenterActionMock.mockRejectedValue(
      new ControlCenterPreflightError("Dry-run preflight is not ready.", {
        schemaVersion: 2,
        status: "blocked",
        dryRunAllowed: false,
        executeAllowed: false,
        checks: [],
        blockers: ["p7_action_readiness_not_ready"],
      }),
    )
    const { POST } = await import("./route")
    const response = await POST(actionRequest({ Origin: "http://localhost" }))
    const payload = await response.json()

    expect(response.status).toBe(409)
    expect(payload.preflight.blockers).toEqual(["p7_action_readiness_not_ready"])
  })

  it("sanitizes generic action errors before returning JSON", async () => {
    runControlCenterActionMock.mockRejectedValue(
      new Error("Unknown action token=secret-token-value C:\\Users\\zycie\\AppData\\Local\\Solteria\\client /tmp/ctoa/action-error/latest.json"),
    )
    const { POST } = await import("./route")
    const response = await POST(actionRequest({ Origin: "http://localhost" }))
    const payload = await response.json()

    expect(response.status).toBe(400)
    expect(payload.error).toContain("token=[redacted]")
    expect(payload.error).toContain("[external]/client")
    expect(payload.error).not.toContain("secret-token-value")
    expect(payload.error).not.toContain("C:\\Users\\zycie")
  })
})
