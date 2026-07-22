import { beforeEach, describe, expect, it, vi } from "vitest"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())
const collectControlCenterOpsMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

vi.mock("@/lib/controlCenterOps", () => ({
  collectControlCenterOps: collectControlCenterOpsMock,
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

function allowAccess() {
  return {
    ok: true,
    viewer: { username: "operator", displayName: "Operator", role: "operator" },
  }
}

function rawOpsWithSensitiveValues() {
  return {
    generatedAt: "2026-07-22T10:00:00.000Z",
    source: { mode: "local", label: "C:\\Users\\operator-one\\private-source" },
    tiles: [
      {
        id: "repo-hygiene",
        label: "Injected label",
        status: "online",
        headline: "C:\\Users\\operator-one\\workspace",
        detail: "Run powershell.exe -File private.ps1 token=do-not-send",
        source: "C:\\Users\\operator-one\\runtime\\private.json",
        updatedAt: "2026-07-22T10:00:00.000Z",
      },
    ],
    details: {
      repoHygiene: {
        status: "PASS",
        findingCount: 3,
        summary: { private_count: 1, public_count: 2, review_count: 3, "operator-one": 99 },
        sourcePath: "C:\\Users\\operator-one\\repo-hygiene.json",
      },
      latestReleaseEvidence: { path: "C:\\Users\\operator-one\\release-secret.md", modifiedAt: "2026-07-22T09:00:00.000Z" },
      releaseEvidenceDrilldown: { fileCount: 4, sprintCount: 2, recentFiles: [{ path: "private-release.md" }] },
      releaseComparison: { relation: "current", nextAction: "powershell.exe -File private.ps1" },
      apiCostReport: {
        status: "ready",
        recordsSeen: 8,
        totalTokens: 144,
        totalCostUsd: 1.239,
        anomalyCount: 1,
        evalArtifacts: { datasetCases: 2, promptVariantCount: 5, datasetPath: "C:\\Users\\operator-one\\dataset.jsonl" },
      },
      controlCenterAudit: { status: "ready", recordCount: 3, sourcePath: "C:\\Users\\operator-one\\audit.jsonl" },
      actionAuditDrilldown: {
        status: "ready",
        recordCount: 3,
        dryRunCount: 2,
        failedCount: 0,
        invalidRecordCount: 1,
        riskCounts: { safe_write: 2, "operator-one": 1 },
        actionCounts: { "powershell.exe -File private.ps1": 1 },
        recentRecords: [{ actor: "operator-one", command: "powershell.exe -File private.ps1", output: "token=do-not-send" }],
      },
      engineBrain: {
        status: "ready",
        p6ReadinessStatus: "ready_for_plugin_design",
        p6PluginHandoff: { status: "ready" },
        p7OperatorBriefStatus: "ready",
        p7ActionReadinessStatus: "safe_write_tools_enabled",
        p7SafeWriteToolDesignStatus: "implemented",
        p7Decision: "powershell.exe -File private.ps1",
        p7HardBlockerCount: 0,
        p7WarningCount: 1,
        p7McpWriteToolCount: 7,
        p7EnabledSafeWriteToolCount: 7,
        p7ReadySafeWriteAuditCount: 7,
        p7SafeWriteAuditCount: 7,
        p7CockpitSmoke: { status: "ready" },
        p7SafeWriteDryRunSmoke: { status: "ready", dryRunReadyCount: 7, preflightReadyCount: 7, safeWriteToolCount: 7 },
        sourcePaths: { manifest: "C:\\Users\\operator-one\\manifest.json" },
      },
      operatorNext: { status: "ready", title: "operator-one", detail: "Run powershell.exe -File private.ps1" },
      recommendations: ["Run powershell.exe -File private.ps1 as operator-one"],
    },
  }
}

describe("Control Center public ops route", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    collectControlCenterOpsMock.mockReset()
    requireControlCenterReadAccessMock.mockResolvedValue(allowAccess())
  })

  it("requires the same read access before collecting internal ops", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess())
    const { GET } = await import("./route")

    const response = await GET()

    expect(response.status).toBe(401)
    expect(response.headers.get("Cache-Control")).toBe("private, no-store, max-age=0")
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center public ops")
    expect(collectControlCenterOpsMock).not.toHaveBeenCalled()
  })

  it("returns only the bounded projection with private no-store caching", async () => {
    collectControlCenterOpsMock.mockResolvedValue(rawOpsWithSensitiveValues())
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()
    const serialized = JSON.stringify(payload)

    expect(response.status).toBe(200)
    expect(response.headers.get("Cache-Control")).toBe("private, no-store, max-age=0")
    expect(response.headers.get("Vary")).toBe("Cookie")
    expect(payload.tiles).toEqual([{ id: "repo-hygiene", label: "Repo hygiene", status: "online" }])
    expect(payload.details.repoHygiene).toEqual({
      status: "ready",
      findingCount: 3,
      summary: { private_count: 1, public_count: 2, review_count: 3 },
    })
    expect(payload.details.controlCenterAudit.actionCounts).toEqual({ recorded: 3 })

    for (const sensitiveValue of [
      "C:\\Users\\operator-one",
      "operator-one",
      "powershell.exe",
      "private.ps1",
      "do-not-send",
      "release-secret.md",
      "Injected label",
    ]) {
      expect(serialized).not.toContain(sensitiveValue)
    }
  })

  it("returns a generic private failure instead of leaking collection errors", async () => {
    collectControlCenterOpsMock.mockRejectedValue(new Error("token=do-not-send C:\\Users\\operator-one\\private.json"))
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(503)
    expect(response.headers.get("Cache-Control")).toBe("private, no-store, max-age=0")
    expect(payload).toEqual({ ok: false, error: "Control Center public status is unavailable." })
    expect(JSON.stringify(payload)).not.toContain("do-not-send")
    expect(JSON.stringify(payload)).not.toContain("operator-one")
  })
})
