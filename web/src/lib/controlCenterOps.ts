import { readFile } from "node:fs/promises"
import path from "node:path"
import { collectControlCenterEvidence, type ControlCenterEvidence } from "@/lib/controlCenterEvidence"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"

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
        source: config.qualityPath,
        updatedAt: evidence.generatedAt,
      },
      {
        id: "release-evidence",
        label: "Release evidence",
        status: releaseStatus,
        headline: evidence.latestReleaseEvidence ? path.basename(evidence.latestReleaseEvidence.path) : "Missing",
        detail: evidence.latestReleaseEvidence
          ? `${evidence.releaseEvidenceFileCount} evidence files across ${evidence.releaseSprints.length} sprint folders.`
          : `No markdown evidence found under ${config.releasesDir}.`,
        source: evidence.latestReleaseEvidence?.path || config.releasesDir,
        updatedAt: evidence.generatedAt,
      },
      {
        id: "api-cost",
        label: "API cost report",
        status: costStatus,
        headline: `${evidence.apiCostReport.recordsSeen} rows`,
        detail: summarizeApiCostReport(evidence.apiCostReport.totalTokens, evidence.apiCostReport.totalCostUsd, evidence.apiCostReport.anomalyCount),
        source: config.costReportPath,
        updatedAt: evidence.generatedAt,
      },
      {
        id: "control-center-audit",
        label: "Control Center audit",
        status: auditStatus,
        headline: `${evidence.controlCenterAudit.recordCount} records`,
        detail: summarizeAuditTrail(evidence.controlCenterAudit.recordCount, recentActions),
        source: config.actionAuditPath,
        updatedAt: evidence.generatedAt,
      },
    ],
    details: {
      repoHygiene: {
        status: evidence.repoHygiene.status,
        findingCount: evidence.repoHygiene.findingCount,
        summary: evidence.repoHygiene.summary,
        sourcePath: config.qualityPath,
      },
      latestReleaseEvidence: evidence.latestReleaseEvidence,
      releaseEvidenceFileCount: evidence.releaseEvidenceFileCount,
      releaseSprints: evidence.releaseSprints,
      apiCostReport: {
        status: evidence.apiCostReport.status,
        recordsSeen: evidence.apiCostReport.recordsSeen,
        totalTokens: evidence.apiCostReport.totalTokens,
        totalCostUsd: evidence.apiCostReport.totalCostUsd,
        anomalyCount: evidence.apiCostReport.anomalyCount,
        evalArtifacts: evidence.apiCostReport.evalArtifacts,
        sourcePath: config.costReportPath,
      },
      controlCenterAudit: {
        status: evidence.controlCenterAudit.status,
        recordCount: evidence.controlCenterAudit.recordCount,
        sourcePath: config.actionAuditPath,
        recentActions,
      },
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

async function readRecentAuditActions(filePath: string): Promise<LocalAuditAction[]> {
  try {
    const text = await readFile(filePath, "utf-8")
    return text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-5)
      .map((line) => {
        const record = JSON.parse(line) as Record<string, unknown>
        return {
          at: String(record.at || ""),
          auditId: String(record.audit_id || ""),
          actor: String(record.actor || ""),
          actorRole: String(record.actor_role || ""),
          action: String(record.action || ""),
          target: String(record.target || ""),
          riskClass: String(record.risk_class || ""),
          minimumRole: String(record.minimum_role || ""),
          dryRun: Boolean(record.dry_run),
          ok: Boolean(record.ok),
          authorized: Boolean(record.authorized),
          reason: String(record.reason || ""),
          outputPreview: String(record.output_preview || ""),
        }
      })
  } catch {
    return []
  }
}
