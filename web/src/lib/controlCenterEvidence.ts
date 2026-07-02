import { readdir, readFile, stat } from "node:fs/promises"
import path from "node:path"
import { getControlCenterEvidenceConfig, type ControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"

export type ControlCenterEvidence = {
  generatedAt: string
  config: ControlCenterEvidenceConfig
  latestReleaseEvidence: {
    path: string
    modifiedAt: string
  } | null
  releaseEvidenceFileCount: number
  releaseSprints: Array<{
    sprint: string
    fileCount: number
    latestModifiedAt: string
  }>
  repoHygiene: {
    status: string
    findingCount: number
    summary: {
      private_count?: number
      public_count?: number
      review_count?: number
    }
  }
  apiCostReport: {
    status: string
    recordsSeen: number
    totalTokens: number
    totalCostUsd: number
    anomalyCount: number
    evalArtifacts: {
      datasetPath: string
      datasetCases: number
      categoryCounts: Record<string, number>
      priorityCounts: Record<string, number>
      promptVariantsDir: string
      promptVariantCount: number
      promptVariants: string[]
    }
  }
  controlCenterAudit: {
    status: string
    recordCount: number
  }
  recommendations: string[]
}

type ApiCostReportArtifact = {
  dataset_path?: string
  dataset_cases?: number
  category_counts?: Record<string, number>
  priority_counts?: Record<string, number>
  prompt_variants_dir?: string
  prompt_variant_count?: number
  prompt_variants?: string[]
}

type ReleaseEvidenceFile = {
  path: string
  modifiedAt: string
}

export async function collectControlCenterEvidence(): Promise<ControlCenterEvidence> {
  const config = getControlCenterEvidenceConfig()
  const latestReleaseEvidence = await findLatestReleaseEvidence(config.releasesDir)
  const releaseEvidenceFileCount = await countMarkdownFiles(config.releasesDir)
  const releaseSprints = await listReleaseSprints(config.releasesDir)
  const repoHygiene = await readJsonIfExists(config.qualityPath)
  const apiCostReport = await readJsonIfExists(config.costReportPath)
  const actionAuditRecordCount = await countJsonlRecords(config.actionAuditPath)

  const recommendations: string[] = []
  const repoStatus = String(repoHygiene?.status || "missing")
  if (!repoHygiene) {
    recommendations.push("Run repo hygiene quality generation before sign-off.")
  } else if (repoStatus !== "PASS") {
    recommendations.push("Review repo hygiene findings before treating the pack as release-ready.")
  }

  if (!apiCostReport) {
    recommendations.push(`Generate ${config.costReportPath} with scripts/ops/api_cost_report.py.`)
  } else if (Number(apiCostReport.records_seen || 0) === 0) {
    recommendations.push("Cost report exists but has no records; verify eval artifacts in evals/runs.")
  }

  if (actionAuditRecordCount === 0) {
    recommendations.push("Exercise at least one Control Center action so the audit trail is visible.")
  }

  if (recommendations.length === 0) {
    recommendations.push("Evidence pack is ready for review. Keep fresh traces attached to the release note.")
  }

  const evalArtifacts = (apiCostReport?.eval_artifacts as ApiCostReportArtifact | undefined) || {}

  return {
    generatedAt: new Date().toISOString(),
    config,
    latestReleaseEvidence,
    releaseEvidenceFileCount,
    releaseSprints,
    repoHygiene: {
      status: repoStatus,
      findingCount: Number(repoHygiene?.finding_count || 0),
      summary: repoHygiene?.summary || {},
    },
    apiCostReport: {
      status: apiCostReport ? "ready" : "missing",
      recordsSeen: Number(apiCostReport?.records_seen || 0),
      totalTokens: Number(apiCostReport?.total_tokens || 0),
      totalCostUsd: Number(apiCostReport?.total_cost_usd || 0),
      anomalyCount: Array.isArray(apiCostReport?.anomalies) ? apiCostReport.anomalies.length : 0,
      evalArtifacts: {
        datasetPath: String(evalArtifacts.dataset_path || "evals/azure-activity-agent-eval-dataset.template.jsonl"),
        datasetCases: Number(evalArtifacts.dataset_cases || 0),
        categoryCounts: evalArtifacts.category_counts || {},
        priorityCounts: evalArtifacts.priority_counts || {},
        promptVariantsDir: String(evalArtifacts.prompt_variants_dir || "evals/prompt-variants"),
        promptVariantCount: Number(evalArtifacts.prompt_variant_count || 0),
        promptVariants: evalArtifacts.prompt_variants || [],
      },
    },
    controlCenterAudit: {
      status: actionAuditRecordCount ? "ready" : "missing",
      recordCount: actionAuditRecordCount,
    },
    recommendations,
  }
}

async function readJsonIfExists(filePath: string): Promise<Record<string, unknown> | null> {
  try {
    const text = await readFile(filePath, "utf-8")
    return JSON.parse(text) as Record<string, unknown>
  } catch {
    return null
  }
}

async function countJsonlRecords(filePath: string): Promise<number> {
  try {
    const text = await readFile(filePath, "utf-8")
    return text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean).length
  } catch {
    return 0
  }
}

async function findLatestReleaseEvidence(dirPath: string): Promise<ReleaseEvidenceFile | null> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true })
    let latest: { path: string; modifiedMs: number } | null = null

    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith("sprint-")) {
        continue
      }
      const sprintDir = path.join(dirPath, entry.name)
      const files = await readdir(sprintDir, { withFileTypes: true })
      for (const file of files) {
        if (!file.isFile() || !file.name.endsWith(".md")) {
          continue
        }
        const fullPath = path.join(sprintDir, file.name)
        const fileStat = await stat(fullPath)
        if (!latest || fileStat.mtimeMs > latest.modifiedMs) {
          latest = { path: fullPath, modifiedMs: fileStat.mtimeMs }
        }
      }
    }

    if (!latest) {
      return null
    }

    return {
      path: latest.path.replace(/\\/g, "/"),
      modifiedAt: new Date(latest.modifiedMs).toISOString(),
    }
  } catch {
    return null
  }
}

async function countMarkdownFiles(dirPath: string): Promise<number> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true })
    let count = 0
    for (const entry of entries) {
      const entryPath = path.join(dirPath, entry.name)
      if (entry.isDirectory()) {
        count += await countMarkdownFiles(entryPath)
      } else if (entry.isFile() && entry.name.endsWith(".md")) {
        count += 1
      }
    }
    return count
  } catch {
    return 0
  }
}

async function listReleaseSprints(dirPath: string): Promise<ControlCenterEvidence["releaseSprints"]> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true })
    const sprintDirs = entries.filter((entry) => entry.isDirectory() && entry.name.startsWith("sprint-"))
    sprintDirs.sort((left, right) => right.name.localeCompare(left.name))

    const result: ControlCenterEvidence["releaseSprints"] = []
    for (const entry of sprintDirs.slice(0, 6)) {
      const sprintDir = path.join(dirPath, entry.name)
      const files = await readdir(sprintDir, { withFileTypes: true })
      const mdFiles = files.filter((file) => file.isFile() && file.name.endsWith(".md"))
      let latestModifiedMs = (await stat(sprintDir)).mtimeMs
      for (const file of mdFiles) {
        const fileStat = await stat(path.join(sprintDir, file.name))
        latestModifiedMs = Math.max(latestModifiedMs, fileStat.mtimeMs)
      }
      result.push({
        sprint: entry.name,
        fileCount: mdFiles.length,
        latestModifiedAt: new Date(latestModifiedMs).toISOString(),
      })
    }
    return result
  } catch {
    return []
  }
}
