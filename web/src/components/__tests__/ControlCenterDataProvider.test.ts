import { describe, expect, it } from "vitest"
import { isControlCenterPublicOps, projectControlCenterOpsForPublicApi } from "@/lib/controlCenterPublicOps"

describe("Control Center public ops projection", () => {
  it("keeps bounded statuses and counts while removing commands, paths, and identities", () => {
    const projected = projectControlCenterOpsForPublicApi({
      generatedAt: "2026-07-22T10:00:00.000Z",
      tiles: [
        {
          id: "repo-hygiene",
          status: "online",
          headline: "C:\\Users\\operator-one\\workspace",
          detail: "token=do-not-project",
          source: "C:\\Users\\operator-one\\runtime\\private.json",
          updatedAt: "2026-07-22T10:00:00.000Z",
        },
      ],
      details: {
        repoHygiene: {
          status: "PASS",
          findingCount: 3,
          summary: { private_count: 1, public_count: 2, review_count: 3, operator_one: 99 },
          sourcePath: "C:\\Users\\operator-one\\repo-hygiene.json",
        },
        latestReleaseEvidence: {
          path: "C:\\Users\\operator-one\\release.md",
          modifiedAt: "2026-07-22T09:00:00.000Z",
        },
        releaseEvidenceDrilldown: {
          fileCount: 4,
          sprintCount: 2,
          recentFiles: [{ path: "release-secret.md", title: "Private release", bytes: 12 }],
        },
        releaseComparison: {
          relation: "current",
          currentJsonPath: "C:\\Users\\operator-one\\runtime\\latest.json",
          nextAction: "powershell.exe -File private.ps1",
        },
        apiCostReport: {
          status: "ready",
          recordsSeen: 8,
          totalTokens: 144,
          totalCostUsd: 1.239,
          anomalyCount: 1,
          evalArtifacts: {
            datasetCases: 2,
            promptVariantCount: 5,
            datasetPath: "C:\\Users\\operator-one\\dataset.jsonl",
          },
        },
        controlCenterAudit: {
          status: "ready",
          recordCount: 3,
          sourcePath: "C:\\Users\\operator-one\\audit.jsonl",
          recentActions: [{ actor: "operator-one", reason: "password=hunter2" }],
        },
        actionAuditDrilldown: {
          status: "ready",
          recordCount: 3,
          dryRunCount: 2,
          failedCount: 0,
          invalidRecordCount: 1,
          riskCounts: { safe_write: 2, guarded_write: 1, "operator-one": 40 },
          actionCounts: { "powershell.exe -File private.ps1": 1, "operator-one": 1 },
          recentRecords: [{ auditId: "audit-identity", actor: "operator-one", output: "secret" }],
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
          p7SafeWriteDryRunSmoke: {
            status: "ready",
            dryRunReadyCount: 7,
            preflightReadyCount: 7,
            safeWriteToolCount: 7,
          },
          sourcePaths: { manifest: "C:\\Users\\operator-one\\manifest.json" },
        },
        operatorNext: {
          status: "ready",
          title: "Operator One",
          detail: "Run powershell.exe -File private.ps1",
        },
        recommendations: ["Run powershell.exe -File private.ps1 as operator-one"],
      },
    })

    expect(projected).not.toBeNull()
    expect(isControlCenterPublicOps(projected)).toBe(true)
    expect(projected?.tiles).toEqual([{ id: "repo-hygiene", label: "Repo hygiene", status: "online" }])
    expect(projected?.details.repoHygiene).toMatchObject({ status: "ready", findingCount: 3 })
    expect(projected?.details.controlCenterAudit.actionCounts).toEqual({ recorded: 3 })
    expect(projected?.details.controlCenterAudit.riskCounts).toEqual({
      read_only: 0,
      safe_write: 2,
      guarded_write: 1,
      dangerous: 0,
    })
    expect(projected?.details.engineBrain.p7.decision).toBe("missing")
    expect(projected?.details.recommendations).toEqual([
      "Bounded evidence is ready for operator review. Any write action still requires its own explicit gate.",
    ])

    const serialized = JSON.stringify(projected)
    for (const privateValue of [
      "C:\\Users\\operator-one",
      "operator-one",
      "powershell.exe",
      "hunter2",
      "audit-identity",
      "do-not-project",
      "release-secret.md",
    ]) {
      expect(serialized).not.toContain(privateValue)
    }
  })

  it("fails closed when the internal payload does not have the expected object shape", () => {
    expect(projectControlCenterOpsForPublicApi(null)).toBeNull()
    expect(projectControlCenterOpsForPublicApi({ generatedAt: "2026-07-22T10:00:00.000Z" })).toBeNull()
    expect(isControlCenterPublicOps({ generatedAt: "2026-07-22T10:00:00.000Z" })).toBe(false)
  })
})
