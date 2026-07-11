import path from "node:path"
import {
  collectControlCenterEvidence,
  readBoundedControlCenterActionAuditLines,
  type ControlCenterEvidence,
} from "@/lib/controlCenterEvidence"
import { toControlCenterDisplayPath } from "@/lib/controlCenterDisplayPath"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { sanitizeControlCenterDisplayText } from "@/lib/controlCenterRedaction"

export type OpsStatus = "online" | "warning" | "offline" | "unknown"

export type OpsTile = {
  id: string
  label: string
  status: OpsStatus
  headline: string
  detail: string
  source: string
  updatedAt: string
}

export type LocalAuditAction = {
  at: string
  auditId: string
  actor: string
  actorRole: string
  action: string
  target: string
  riskClass: string
  minimumRole: string
  dryRun: boolean
  ok: boolean
  authorized: boolean
  reason: string
  outputPreview: string
}

export type ControlCenterOps = {
  generatedAt: string
  source: {
    mode: "local"
    label: string
  }
  tiles: OpsTile[]
  details: {
    repoHygiene: {
      status: string
      findingCount: number
      summary: ControlCenterEvidence["repoHygiene"]["summary"]
      sourcePath: string
    }
    latestReleaseEvidence: ControlCenterEvidence["latestReleaseEvidence"]
    releaseEvidenceFileCount: number
    releaseSprints: ControlCenterEvidence["releaseSprints"]
    releaseEvidenceDrilldown: ControlCenterEvidence["releaseEvidenceDrilldown"]
    releaseComparison: ControlCenterEvidence["releaseComparison"]
    apiCostReport: {
      status: string
      recordsSeen: number
      totalTokens: number
      totalCostUsd: number
      anomalyCount: number
      evalArtifacts: ControlCenterEvidence["apiCostReport"]["evalArtifacts"]
      sourcePath: string
    }
    controlCenterAudit: {
      status: string
      recordCount: number
      sourcePath: string
      recentActions: LocalAuditAction[]
    }
    engineBrain: ControlCenterEvidence["engineBrain"]
    operatorNext: ControlCenterEvidence["operatorNext"]
    actionAuditDrilldown: ControlCenterEvidence["actionAuditDrilldown"]
    recommendations: string[]
  }
}

export async function collectControlCenterOps(): Promise<ControlCenterOps> {
  const evidence = await collectControlCenterEvidence()
  const config = getControlCenterEvidenceConfig()
  const recentActions = await readRecentAuditActions(config.actionAuditPath)

  const repoStatus = evidence.repoHygiene.status === "PASS" ? "online" : evidence.repoHygiene.status === "FAIL" ? "offline" : "warning"
  const releaseStatus = evidence.latestReleaseEvidence ? "online" : "warning"
  const costStatus =
    evidence.apiCostReport.status === "ready" && evidence.apiCostReport.recordsSeen > 0
      ? "online"
      : evidence.apiCostReport.status === "ready"
        ? "warning"
        : "warning"
  const auditStatus = evidence.controlCenterAudit.recordCount > 0 ? "online" : "warning"
  const engineBrainStatus =
    evidence.engineBrain.status === "ready" ? "online" : evidence.engineBrain.status === "blocked" ? "offline" : "warning"
  const operatorNextStatus =
    evidence.operatorNext.status === "ready" ? "online" : evidence.operatorNext.status === "blocked" ? "offline" : "warning"

  return {
    generatedAt: evidence.generatedAt,
    source: {
      mode: "local",
      label: "Local file-backed status",
    },
    tiles: [
      {
        id: "repo-hygiene",
        label: "Repo hygiene",
        status: repoStatus,
        headline: evidence.repoHygiene.status,
        detail: summarizeRepoHygiene(evidence.repoHygiene.findingCount, evidence.repoHygiene.summary),
        source: toControlCenterDisplayPath(config.qualityPath),
        updatedAt: evidence.generatedAt,
      },
      {
        id: "release-evidence",
        label: "Release evidence",
        status: releaseStatus,
        headline: evidence.latestReleaseEvidence ? path.basename(evidence.latestReleaseEvidence.path) : "Missing",
        detail: evidence.latestReleaseEvidence
          ? `${evidence.releaseEvidenceDrilldown.fileCount} evidence files across ${evidence.releaseEvidenceDrilldown.sprintCount} sprint folders.`
          : `No markdown evidence found under ${config.releasesDir}.`,
        source: evidence.latestReleaseEvidence?.path || toControlCenterDisplayPath(config.releasesDir),
        updatedAt: evidence.generatedAt,
      },
      {
        id: "api-cost",
        label: "API cost report",
        status: costStatus,
        headline: `${evidence.apiCostReport.recordsSeen} rows`,
        detail: summarizeApiCostReport(evidence.apiCostReport.totalTokens, evidence.apiCostReport.totalCostUsd, evidence.apiCostReport.anomalyCount),
        source: toControlCenterDisplayPath(config.costReportPath),
        updatedAt: evidence.generatedAt,
      },
      {
        id: "control-center-audit",
        label: "Control Center audit",
        status: auditStatus,
        headline: `${evidence.controlCenterAudit.recordCount} records`,
        detail: summarizeAuditTrail(evidence.controlCenterAudit.recordCount, recentActions),
        source: toControlCenterDisplayPath(config.actionAuditPath),
        updatedAt: evidence.generatedAt,
      },
      {
        id: "engine-brain",
        label: "Engine Brain",
        status: engineBrainStatus,
        headline: evidence.engineBrain.p7Decision || evidence.engineBrain.status,
        detail: summarizeEngineBrain(evidence.engineBrain),
        source: evidence.engineBrain.sourcePaths.operatorBrief,
        updatedAt: evidence.generatedAt,
      },
      {
        id: "operator-next",
        label: "Operator next",
        status: operatorNextStatus,
        headline: evidence.operatorNext.title,
        detail: `${evidence.operatorNext.lane} · ${evidence.operatorNext.riskClass} · ${evidence.operatorNext.detail}`,
        source: evidence.operatorNext.sourcePath,
        updatedAt: evidence.generatedAt,
      },
    ],
    details: {
      repoHygiene: {
        status: evidence.repoHygiene.status,
        findingCount: evidence.repoHygiene.findingCount,
        summary: evidence.repoHygiene.summary,
        sourcePath: toControlCenterDisplayPath(config.qualityPath),
      },
      latestReleaseEvidence: evidence.latestReleaseEvidence,
      releaseEvidenceFileCount: evidence.releaseEvidenceFileCount,
      releaseSprints: evidence.releaseSprints,
      releaseEvidenceDrilldown: evidence.releaseEvidenceDrilldown,
      releaseComparison: evidence.releaseComparison,
      apiCostReport: {
        status: evidence.apiCostReport.status,
        recordsSeen: evidence.apiCostReport.recordsSeen,
        totalTokens: evidence.apiCostReport.totalTokens,
        totalCostUsd: evidence.apiCostReport.totalCostUsd,
        anomalyCount: evidence.apiCostReport.anomalyCount,
        evalArtifacts: evidence.apiCostReport.evalArtifacts,
        sourcePath: toControlCenterDisplayPath(config.costReportPath),
      },
      controlCenterAudit: {
        status: evidence.controlCenterAudit.status,
        recordCount: evidence.controlCenterAudit.recordCount,
        sourcePath: toControlCenterDisplayPath(config.actionAuditPath),
        recentActions,
      },
      engineBrain: evidence.engineBrain,
      operatorNext: evidence.operatorNext,
      actionAuditDrilldown: evidence.actionAuditDrilldown,
      recommendations: evidence.recommendations,
    },
  }
}

function summarizeRepoHygiene(findingCount: number, summary: ControlCenterEvidence["repoHygiene"]["summary"]): string {
  const privateCount = Number(summary.private_count || 0)
  const publicCount = Number(summary.public_count || 0)
  const reviewCount = Number(summary.review_count || 0)
  return `${findingCount} findings · private ${privateCount} · public ${publicCount} · review ${reviewCount}`
}

function summarizeApiCostReport(totalTokens: number, totalCostUsd: number, anomalyCount: number): string {
  return `${totalTokens} tokens · $${totalCostUsd.toFixed(2)} · ${anomalyCount} anomalies`
}

function summarizeAuditTrail(recordCount: number, recentActions: LocalAuditAction[]): string {
  const latest = recentActions[recentActions.length - 1]
  if (!latest) {
    return recordCount > 0 ? `${recordCount} records captured.` : "No local Control Center actions recorded yet."
  }
  return `${recordCount} records · latest ${latest.action} (${latest.dryRun ? "dry run" : "live"})`
}

function summarizeEngineBrain(engineBrain: ControlCenterEvidence["engineBrain"]): string {
  const safeAuditSummary = engineBrain.p7SafeWriteAuditCount
    ? `${engineBrain.p7ReadySafeWriteAuditCount}/${engineBrain.p7SafeWriteAuditCount}`
    : engineBrain.p7SafeWriteAudit.status
  return `P6 ${engineBrain.p6ReadinessStatus} · plugin ${engineBrain.p6PluginHandoff.status} ${engineBrain.p6PluginHandoff.installedCacheVersion || "no-cache"} · P6 smoke ${engineBrain.p6PluginHandoff.smokeStatus} ${engineBrain.p6PluginHandoff.smokePassedCount}/${engineBrain.p6PluginHandoff.smokeCheckCount} · P7 ${engineBrain.p7OperatorBriefStatus} · MCP ${engineBrain.p7EnabledSafeWriteToolCount} enabled · ${engineBrain.p7OperatorCockpitSummary} · actions ${engineBrain.p7ActionAuditedCandidateCount}/${engineBrain.p7ActionCandidateCount} audited · design ${engineBrain.p7SafeWriteToolDesignStatus} · audits ${safeAuditSummary} · smoke ${engineBrain.p7CockpitSmoke.status} ${engineBrain.p7CockpitSmoke.passedCount}/${engineBrain.p7CockpitSmoke.checkCount} · dry-run ${engineBrain.p7SafeWriteDryRunSmoke.status} ${engineBrain.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount}; preflight ${engineBrain.p7SafeWriteDryRunSmoke.preflightReadyCount}/${engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount}; bootstrap ${engineBrain.p7SafeWriteDryRunSmoke.bootstrapAllowedCount} · pack ${engineBrain.packIncludedCount} sections`
}

async function readRecentAuditActions(filePath: string): Promise<LocalAuditAction[]> {
  try {
    const sample = await readBoundedControlCenterActionAuditLines(filePath)
    return sample.lines
      .slice(-5)
      .map((line) => {
        const record = JSON.parse(line) as Record<string, unknown>
        return {
          at: sanitizeOpsText(String(record.at || ""), 80),
          auditId: sanitizeOpsText(String(record.audit_id || ""), 80),
          actor: sanitizeOpsText(String(record.actor || ""), 80),
          actorRole: sanitizeOpsText(String(record.actor_role || ""), 80),
          action: sanitizeOpsText(String(record.action || ""), 80),
          target: sanitizeOpsText(String(record.target || ""), 80),
          riskClass: sanitizeOpsText(String(record.risk_class || ""), 80),
          minimumRole: sanitizeOpsText(String(record.minimum_role || ""), 80),
          dryRun: Boolean(record.dry_run),
          ok: Boolean(record.ok),
          authorized: Boolean(record.authorized),
          reason: sanitizeOpsText(String(record.reason || ""), 160),
          outputPreview: sanitizeOpsText(String(record.output_preview || ""), 240),
        }
      })
  } catch {
    return []
  }
}

function sanitizeOpsText(value: string, maxLength: number): string {
  return sanitizeControlCenterDisplayText(value, maxLength)
}
