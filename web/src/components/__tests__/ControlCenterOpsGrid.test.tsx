import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import type { ControlCenterDataState, ControlCenterPublicOps } from "@/components/ControlCenterDataProvider"

const mockedDataState = vi.hoisted(() => ({ value: null as unknown }))

vi.mock("@/components/ControlCenterDataProvider", () => ({
  useControlCenterData: () => mockedDataState.value,
}))

import ControlCenterOpsGrid from "../ControlCenterOpsGrid"

describe("ControlCenterOpsGrid", () => {
  it("renders only bounded tile labels and statuses, never raw detail or source fields", () => {
    const sensitiveValue = "C:\\Users\\operator-one\\run-private.ps1 token=do-not-render"
    mockedDataState.value = {
      state: "ready",
      error: null,
      data: {
        generatedAt: "2026-07-22T10:00:00.000Z",
        tiles: [
          {
            id: "repo-hygiene",
            label: "Repo hygiene",
            status: "online",
            headline: sensitiveValue,
            detail: sensitiveValue,
            source: sensitiveValue,
          },
        ],
        details: {
          repoHygiene: { status: "ready", findingCount: 0, summary: {} },
          releaseEvidence: { status: "missing", fileCount: 0, sprintCount: 0, relation: "missing", latestUpdatedAt: "" },
          apiCostReport: { status: "missing", recordsSeen: 0, totalTokens: 0, totalCostUsd: 0, anomalyCount: 0, datasetCases: 0, promptVariantCount: 0 },
          controlCenterAudit: { status: "missing", recordCount: 0, dryRunCount: 0, failedCount: 0, invalidRecordCount: 0, riskCounts: {}, actionCounts: {} },
          engineBrain: {
            status: "missing",
            p6ReadinessStatus: "missing",
            p6PluginHandoffStatus: "missing",
            p7: {
              operatorBriefStatus: "missing",
              actionReadinessStatus: "missing",
              safeWriteToolDesignStatus: "missing",
              decision: "missing",
              blockerCount: 0,
              warningCount: 0,
              mcpWriteToolCount: 0,
              enabledSafeWriteToolCount: 0,
              readySafeWriteAuditCount: 0,
              safeWriteAuditCount: 0,
              cockpitSmokeStatus: "missing",
              dryRunSmokeStatus: "missing",
              dryRunReadyCount: 0,
              preflightReadyCount: 0,
              safeWriteToolCount: 0,
            },
          },
          operatorNext: { status: "missing" },
          recommendations: [],
        },
      } as unknown as ControlCenterPublicOps,
    } satisfies ControlCenterDataState

    const markup = renderToStaticMarkup(<ControlCenterOpsGrid />)

    expect(markup).toContain("Repo hygiene")
    expect(markup).toContain("online")
    expect(markup).toContain("Bounded status; operational details are intentionally not displayed.")
    expect(markup).not.toContain(sensitiveValue)
    expect(markup).not.toContain("run-private.ps1")
    expect(markup).not.toContain("operator-one")
  })
})
