import { lstat, readdir } from "node:fs/promises"
import { sanitizeControlCenterDisplayText } from "@/lib/controlCenterRedaction"
import {
  jsonHasDuplicateObjectKeys,
  readBoundedControlCenterActionAuditLines,
  readStrictControlCenterJson,
} from "@/lib/controlCenterEvidenceIo"

export const RELEASE_SPRINT_LIMIT = 24
export const RELEASE_FILE_LIMIT = 80
const AUDIT_LINE_MAX_CHARS = 16 * 1024
const RECENT_AUDIT_OUTCOME_LIMIT = 6

export type PublicEvidenceStatus = "ready" | "warn" | "blocked" | "missing"

export type RepoHygieneCapabilityEvidence = {
  status: PublicEvidenceStatus
  findingCount: number
  privateCount: number
  publicCount: number
  reviewCount: number
}

export type ApiCostCapabilityEvidence = {
  status: PublicEvidenceStatus
  recordsSeen: number
  totalTokens: number
  totalCostUsd: number
  anomalyCount: number
  datasetCases: number
  promptVariantCount: number
}

export type ControlCenterAuditCapabilityEvidence = {
  status: PublicEvidenceStatus
  recordCount: number
  invalidRecordCount: number
  truncated: boolean
  dryRunCount: number
  authorizedCount: number
  deniedCount: number
  failedCount: number
  outcomes: Array<{
    action: string
    riskClass: string
    outcome: string
    dryRun: boolean
    authorized: boolean | null
  }>
}

export type ReleaseEvidenceCapabilityEvidence = {
  status: PublicEvidenceStatus
  sprintCount: number
  fileCount: number
  latestSprint: string
  latestModifiedAt: string
  truncated: boolean
}

export async function collectRepoHygieneCapability(filePath: string): Promise<RepoHygieneCapabilityEvidence> {
  const payload = await readStrictControlCenterJson(filePath)
  if (!payload) {
    return { status: "missing", findingCount: 0, privateCount: 0, publicCount: 0, reviewCount: 0 }
  }

  const summary = isRecord(payload.summary) ? payload.summary : {}
  const reported = safeText(payload.status, 80).toUpperCase()
  return {
    status: reported === "PASS" ? "ready" : reported === "FAIL" ? "blocked" : "warn",
    findingCount: nonnegativeInteger(payload.finding_count),
    privateCount: nonnegativeInteger(summary.private_count),
    publicCount: nonnegativeInteger(summary.public_count),
    reviewCount: nonnegativeInteger(summary.review_count),
  }
}

export async function collectApiCostCapability(filePath: string): Promise<ApiCostCapabilityEvidence> {
  const payload = await readStrictControlCenterJson(filePath)
  if (!payload) {
    return {
      status: "missing",
      recordsSeen: 0,
      totalTokens: 0,
      totalCostUsd: 0,
      anomalyCount: 0,
      datasetCases: 0,
      promptVariantCount: 0,
    }
  }

  const evalArtifacts = isRecord(payload.eval_artifacts) ? payload.eval_artifacts : {}
  const recordsSeen = nonnegativeInteger(payload.records_seen)
  return {
    status: recordsSeen > 0 ? "ready" : "warn",
    recordsSeen,
    totalTokens: nonnegativeInteger(payload.total_tokens),
    totalCostUsd: nonnegativeNumber(payload.total_cost_usd),
    anomalyCount: Array.isArray(payload.anomalies) ? Math.min(payload.anomalies.length, RELEASE_FILE_LIMIT) : 0,
    datasetCases: nonnegativeInteger(evalArtifacts.dataset_cases),
    promptVariantCount: nonnegativeInteger(evalArtifacts.prompt_variant_count),
  }
}

/**
 * Project only aggregate audit state.  Raw records can contain an actor,
 * audit id, reason, output preview, command, or path, none of which belongs
 * in a Control Center capability payload.
 */
export async function collectControlCenterAuditCapability(
  filePath: string,
): Promise<ControlCenterAuditCapabilityEvidence> {
  try {
    const sample = await readBoundedControlCenterActionAuditLines(filePath)
    const records: Record<string, unknown>[] = []
    let invalidRecordCount = 0

    for (const line of sample.lines) {
      if (line.length > AUDIT_LINE_MAX_CHARS || jsonHasDuplicateObjectKeys(line)) {
        invalidRecordCount += 1
        continue
      }
      try {
        const parsed: unknown = JSON.parse(line)
        if (isRecord(parsed)) records.push(parsed)
        else invalidRecordCount += 1
      } catch {
        invalidRecordCount += 1
      }
    }

    const outcomes = records
      .slice(-RECENT_AUDIT_OUTCOME_LIMIT)
      .reverse()
      .map((record) => ({
        action: safeText(record.action, 80) || "unknown",
        riskClass: safeText(record.risk_class, 80) || "unknown",
        outcome: auditOutcomeSummary(record),
        dryRun: record.dry_run === true,
        authorized: typeof record.authorized === "boolean" ? record.authorized : null,
      }))

    const status: PublicEvidenceStatus =
      records.length === 0 ? (sample.sourceBytes > 0 ? "warn" : "missing") : sample.truncated || invalidRecordCount > 0 ? "warn" : "ready"

    return {
      status,
      recordCount: records.length,
      invalidRecordCount,
      truncated: sample.truncated,
      dryRunCount: records.filter((record) => record.dry_run === true).length,
      authorizedCount: records.filter((record) => record.authorized === true).length,
      deniedCount: records.filter((record) => record.authorized === false).length,
      failedCount: records.filter((record) => record.ok === false).length,
      outcomes,
    }
  } catch {
    return {
      status: "missing",
      recordCount: 0,
      invalidRecordCount: 0,
      truncated: false,
      dryRunCount: 0,
      authorizedCount: 0,
      deniedCount: 0,
      failedCount: 0,
      outcomes: [],
    }
  }
}

export async function collectReleaseEvidenceCapability(releasesDir: string): Promise<ReleaseEvidenceCapabilityEvidence> {
  const bundle = await collectReleaseEvidenceBundle(releasesDir)
  return {
    status: bundle.fileCount > 0 ? (bundle.truncated ? "warn" : "ready") : "missing",
    sprintCount: bundle.sprintCount,
    fileCount: bundle.fileCount,
    latestSprint: bundle.latestSprint,
    latestModifiedAt: bundle.latestModifiedAt,
    truncated: bundle.truncated,
  }
}

/**
 * Scan a small bounded release-evidence index.  This deliberately emits no
 * file names or paths, because filenames can reveal a prompt or private work.
 */
export async function collectReleaseEvidenceBundle(releasesDir: string): Promise<{
  sprintCount: number
  fileCount: number
  latestSprint: string
  latestModifiedAt: string
  truncated: boolean
}> {
  try {
    const root = await lstat(releasesDir)
    if (!root.isDirectory() || root.isSymbolicLink()) return emptyReleaseBundle()

    const entries = await readdir(releasesDir, { withFileTypes: true })
    const candidateSprints = entries
      .filter((entry) => entry.isDirectory() && !entry.isSymbolicLink() && /^sprint-[a-z0-9_-]+$/i.test(entry.name))
      .sort((left, right) => right.name.localeCompare(left.name))
    let truncated = candidateSprints.length > RELEASE_SPRINT_LIMIT
    let sprintCount = 0
    let fileCount = 0
    let latestSprint = ""
    let latestModifiedMs = 0

    for (const sprint of candidateSprints.slice(0, RELEASE_SPRINT_LIMIT)) {
      const sprintPath = `${releasesDir}${releasesDir.endsWith("/") || releasesDir.endsWith("\\") ? "" : "/"}${sprint.name}`
      const sprintInfo = await lstat(sprintPath)
      if (!sprintInfo.isDirectory() || sprintInfo.isSymbolicLink()) continue
      const files = (await readdir(sprintPath, { withFileTypes: true }))
        .filter((file) => file.isFile() && !file.isSymbolicLink() && file.name.toLowerCase().endsWith(".md"))
        .sort((left, right) => right.name.localeCompare(left.name))
      if (files.length > RELEASE_FILE_LIMIT) truncated = true
      let sprintFiles = 0

      for (const file of files.slice(0, RELEASE_FILE_LIMIT)) {
        const filePath = `${sprintPath}/${file.name}`
        const fileInfo = await lstat(filePath)
        if (!fileInfo.isFile() || fileInfo.isSymbolicLink()) continue
        sprintFiles += 1
        fileCount += 1
        if (fileInfo.mtimeMs > latestModifiedMs) {
          latestModifiedMs = fileInfo.mtimeMs
          latestSprint = safeText(sprint.name, 80)
        }
      }
      if (sprintFiles > 0) sprintCount += 1
    }

    return {
      sprintCount,
      fileCount,
      latestSprint,
      latestModifiedAt: latestModifiedMs ? new Date(latestModifiedMs).toISOString() : "",
      truncated,
    }
  } catch {
    return emptyReleaseBundle()
  }
}

/** A path-free, identity-free summary suitable for operator capabilities. */
export function auditOutcomeSummary(record: Record<string, unknown>): string {
  const mode = record.dry_run === true ? "dry-run" : "confirmed"
  const result = record.ok === true ? "completed" : record.ok === false ? "failed" : "unreported"
  const authorization = record.authorized === true ? "authorized" : record.authorized === false ? "denied" : "authorization-unreported"
  return `${mode}; ${result}; ${authorization}`
}

function emptyReleaseBundle() {
  return { sprintCount: 0, fileCount: 0, latestSprint: "", latestModifiedAt: "", truncated: false }
}

function safeText(value: unknown, maxLength: number): string {
  return sanitizeControlCenterDisplayText(typeof value === "string" ? value : "", maxLength)
}

function nonnegativeInteger(value: unknown): number {
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0
}

function nonnegativeNumber(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}
