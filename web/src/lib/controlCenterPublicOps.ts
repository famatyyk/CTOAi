/**
 * The browser-facing Control Center ops contract.  This is deliberately a
 * smaller shape than `ControlCenterOps`: it contains statuses, bounded counts,
 * and timestamps only.  Paths, commands, identities, audit records, reasons,
 * outputs, and source-provided prose must never be added here.
 */

const MAX_COUNT = 1_000_000_000
const MAX_COUNT_MAP_ENTRIES = 8

export type PublicOpsStatus = "online" | "warning" | "offline" | "unknown"
export type PublicCapabilityStatus = "ready" | "warn" | "blocked" | "missing"
export type PublicReadinessStatus = "ready" | "needs_attention" | "blocked" | "missing"

export type ControlCenterPublicOps = {
  generatedAt: string
  tiles: Array<{
    id: string
    label: string
    status: PublicOpsStatus
  }>
  details: {
    repoHygiene: {
      status: PublicReadinessStatus
      findingCount: number
      summary: Record<string, number>
    }
    releaseEvidence: {
      status: PublicReadinessStatus
      fileCount: number
      sprintCount: number
      relation: PublicReadinessStatus
      latestUpdatedAt: string
    }
    apiCostReport: {
      status: PublicReadinessStatus
      recordsSeen: number
      totalTokens: number
      totalCostUsd: number
      anomalyCount: number
      datasetCases: number
      promptVariantCount: number
    }
    controlCenterAudit: {
      status: PublicReadinessStatus
      recordCount: number
      dryRunCount: number
      failedCount: number
      invalidRecordCount: number
      riskCounts: Record<string, number>
      actionCounts: Record<string, number>
    }
    engineBrain: {
      status: PublicCapabilityStatus
      p6ReadinessStatus: PublicReadinessStatus
      p6PluginHandoffStatus: PublicCapabilityStatus
      p7: {
        operatorBriefStatus: PublicReadinessStatus
        actionReadinessStatus: PublicReadinessStatus
        safeWriteToolDesignStatus: PublicReadinessStatus
        decision: PublicReadinessStatus
        blockerCount: number
        warningCount: number
        mcpWriteToolCount: number
        enabledSafeWriteToolCount: number
        readySafeWriteAuditCount: number
        safeWriteAuditCount: number
        cockpitSmokeStatus: PublicReadinessStatus
        dryRunSmokeStatus: PublicReadinessStatus
        dryRunReadyCount: number
        preflightReadyCount: number
        safeWriteToolCount: number
      }
    }
    operatorNext: {
      status: PublicCapabilityStatus
    }
    recommendations: string[]
  }
}

/**
 * Server-side projection for the public ops route.  It accepts the internal
 * collection shape as unknown on purpose, then copies only explicit,
 * allowlisted status/count fields into a new object.
 */
export function projectControlCenterOpsForPublicApi(value: unknown): ControlCenterPublicOps | null {
  const root = asRecord(value)
  const details = asRecord(root?.details)
  if (!root || !details) return null

  const repoHygiene = asRecord(details.repoHygiene)
  const releaseDrilldown = asRecord(details.releaseEvidenceDrilldown)
  const releaseComparison = asRecord(details.releaseComparison)
  const apiCostReport = asRecord(details.apiCostReport)
  const evalArtifacts = asRecord(apiCostReport?.evalArtifacts)
  const controlCenterAudit = asRecord(details.controlCenterAudit)
  const actionAuditDrilldown = asRecord(details.actionAuditDrilldown)
  const engineBrain = asRecord(details.engineBrain)
  const p6PluginHandoff = asRecord(engineBrain?.p6PluginHandoff)
  const p7CockpitSmoke = asRecord(engineBrain?.p7CockpitSmoke)
  const p7DryRunSmoke = asRecord(engineBrain?.p7SafeWriteDryRunSmoke)
  const operatorNext = asRecord(details.operatorNext)
  const latestReleaseEvidence = asRecord(details.latestReleaseEvidence)

  return {
    generatedAt: safeTimestamp(root.generatedAt),
    tiles: projectTiles(root.tiles),
    details: {
      repoHygiene: {
        status: publicReadiness(repoHygiene?.status),
        findingCount: safeCount(repoHygiene?.findingCount),
        summary: projectCountMap(repoHygiene?.summary, ["private_count", "public_count", "review_count"]),
      },
      releaseEvidence: {
        status: latestReleaseEvidence ? "ready" : "missing",
        fileCount: safeCount(releaseDrilldown?.fileCount ?? details.releaseEvidenceFileCount),
        sprintCount: safeCount(releaseDrilldown?.sprintCount),
        relation: publicReadiness(releaseComparison?.relation),
        latestUpdatedAt: safeTimestamp(latestReleaseEvidence?.modifiedAt),
      },
      apiCostReport: {
        status: publicReadiness(apiCostReport?.status),
        recordsSeen: safeCount(apiCostReport?.recordsSeen),
        totalTokens: safeCount(apiCostReport?.totalTokens),
        totalCostUsd: safeCurrency(apiCostReport?.totalCostUsd),
        anomalyCount: safeCount(apiCostReport?.anomalyCount),
        datasetCases: safeCount(evalArtifacts?.datasetCases),
        promptVariantCount: safeCount(evalArtifacts?.promptVariantCount),
      },
      controlCenterAudit: {
        status: publicReadiness(actionAuditDrilldown?.status ?? controlCenterAudit?.status),
        recordCount: safeCount(actionAuditDrilldown?.recordCount ?? controlCenterAudit?.recordCount),
        dryRunCount: safeCount(actionAuditDrilldown?.dryRunCount),
        failedCount: safeCount(actionAuditDrilldown?.failedCount),
        invalidRecordCount: safeCount(actionAuditDrilldown?.invalidRecordCount),
        riskCounts: projectCountMap(actionAuditDrilldown?.riskCounts, ["read_only", "safe_write", "guarded_write", "dangerous"]),
        actionCounts: { recorded: safeCount(actionAuditDrilldown?.recordCount ?? controlCenterAudit?.recordCount) },
      },
      engineBrain: {
        status: safeCapabilityStatus(engineBrain?.status),
        p6ReadinessStatus: publicReadiness(engineBrain?.p6ReadinessStatus),
        p6PluginHandoffStatus: safeCapabilityStatus(p6PluginHandoff?.status),
        p7: {
          operatorBriefStatus: publicReadiness(engineBrain?.p7OperatorBriefStatus),
          actionReadinessStatus: publicReadiness(engineBrain?.p7ActionReadinessStatus),
          safeWriteToolDesignStatus: publicReadiness(engineBrain?.p7SafeWriteToolDesignStatus),
          decision: publicReadiness(engineBrain?.p7Decision),
          blockerCount: safeCount(engineBrain?.p7HardBlockerCount),
          warningCount: safeCount(engineBrain?.p7WarningCount),
          mcpWriteToolCount: safeCount(engineBrain?.p7McpWriteToolCount),
          enabledSafeWriteToolCount: safeCount(engineBrain?.p7EnabledSafeWriteToolCount),
          readySafeWriteAuditCount: safeCount(engineBrain?.p7ReadySafeWriteAuditCount),
          safeWriteAuditCount: safeCount(engineBrain?.p7SafeWriteAuditCount),
          cockpitSmokeStatus: publicReadiness(p7CockpitSmoke?.status),
          dryRunSmokeStatus: publicReadiness(p7DryRunSmoke?.status),
          dryRunReadyCount: safeCount(p7DryRunSmoke?.dryRunReadyCount),
          preflightReadyCount: safeCount(p7DryRunSmoke?.preflightReadyCount),
          safeWriteToolCount: safeCount(p7DryRunSmoke?.safeWriteToolCount),
        },
      },
      operatorNext: {
        status: safeCapabilityStatus(operatorNext?.status),
      },
      recommendations: publicRecommendations(engineBrain?.status),
    },
  }
}

/**
 * Lightweight shape check for the client transport.  The server route owns
 * projection; the browser only accepts that already-bounded contract.
 */
export function isControlCenterPublicOps(value: unknown): value is ControlCenterPublicOps {
  const root = asRecord(value)
  const details = asRecord(root?.details)
  return Boolean(
    root &&
      details &&
      typeof root.generatedAt === "string" &&
      Array.isArray(root.tiles) &&
      asRecord(details.repoHygiene) &&
      asRecord(details.releaseEvidence) &&
      asRecord(details.apiCostReport) &&
      asRecord(details.controlCenterAudit) &&
      asRecord(details.engineBrain) &&
      asRecord(details.operatorNext) &&
      Array.isArray(details.recommendations),
  )
}

function projectTiles(value: unknown): ControlCenterPublicOps["tiles"] {
  const tiles = Array.isArray(value) ? value : []
  const allowedLabels: Record<string, string> = {
    "repo-hygiene": "Repo hygiene",
    "release-evidence": "Release evidence",
    "api-cost": "API cost report",
    "control-center-audit": "Control Center audit",
    "engine-brain": "Engine Brain",
    "operator-next": "Operator next",
  }

  return tiles.slice(0, 6).flatMap((candidate) => {
    const tile = asRecord(candidate)
    const id = typeof tile?.id === "string" ? tile.id : ""
    const label = allowedLabels[id]
    if (!label) return []

    return [{ id, label, status: safeOpsStatus(tile?.status) }]
  })
}

function publicRecommendations(engineBrainStatus: unknown): string[] {
  const status = safeCapabilityStatus(engineBrainStatus)
  if (status === "ready") {
    return ["Bounded evidence is ready for operator review. Any write action still requires its own explicit gate."]
  }
  return ["Review the bounded Control Center evidence before authorizing any follow-up action."]
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

function safeCount(value: unknown): number {
  const numberValue = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(numberValue) || numberValue < 0) return 0
  return Math.min(Math.floor(numberValue), MAX_COUNT)
}

function safeCurrency(value: unknown): number {
  const numberValue = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(numberValue) || numberValue < 0) return 0
  return Math.min(Math.round(numberValue * 100) / 100, MAX_COUNT)
}

function safeTimestamp(value: unknown): string {
  if (typeof value !== "string") return ""
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? "" : new Date(timestamp).toISOString()
}

function safeOpsStatus(value: unknown): PublicOpsStatus {
  return value === "online" || value === "warning" || value === "offline" || value === "unknown" ? value : "unknown"
}

function safeCapabilityStatus(value: unknown): PublicCapabilityStatus {
  return value === "ready" || value === "warn" || value === "blocked" || value === "missing" ? value : "missing"
}

function publicReadiness(value: unknown): PublicReadinessStatus {
  if (typeof value !== "string") return "missing"
  const normalized = value.toLowerCase()
  if (/(blocked|failed|fail|offline|denied)/.test(normalized)) return "blocked"
  if (/(missing|not_ready|unknown|unavailable)/.test(normalized)) return "missing"
  if (/(warn|attention|stale|pending|review|aging)/.test(normalized)) return "needs_attention"
  if (/(ready|pass|enabled|online|complete|implement)/.test(normalized)) return "ready"
  return "missing"
}

function projectCountMap(value: unknown, allowedKeys: string[]): Record<string, number> {
  const record = asRecord(value)
  if (!record) return {}
  return Object.fromEntries(allowedKeys.slice(0, MAX_COUNT_MAP_ENTRIES).map((key) => [key, safeCount(record[key])]))
}
