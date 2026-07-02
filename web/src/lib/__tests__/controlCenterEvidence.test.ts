import { afterEach, describe, expect, it } from "vitest"
import { mkdir, mkdtemp, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { collectControlCenterEvidence } from "../controlCenterEvidence"
import { getControlCenterEvidenceConfig } from "../controlCenterEvidenceConfig"

const originalEnv = {
  CTOA_RELEASES_DIR: process.env.CTOA_RELEASES_DIR,
  CTOA_REPO_HYGIENE_PATH: process.env.CTOA_REPO_HYGIENE_PATH,
  CTOA_API_COST_REPORT_PATH: process.env.CTOA_API_COST_REPORT_PATH,
  CTOA_ACTION_AUDIT_PATH: process.env.CTOA_ACTION_AUDIT_PATH,
  CTOA_EVIDENCE_JSON_PATH: process.env.CTOA_EVIDENCE_JSON_PATH,
  CTOA_EVIDENCE_MD_PATH: process.env.CTOA_EVIDENCE_MD_PATH,
  CTOA_API_COST_MD_OUT: process.env.CTOA_API_COST_MD_OUT,
  CTOA_API_COST_MD_PATH: process.env.CTOA_API_COST_MD_PATH,
  CTOA_EVAL_DATASET_PATH: process.env.CTOA_EVAL_DATASET_PATH,
  CTOA_PROMPT_VARIANTS_DIR: process.env.CTOA_PROMPT_VARIANTS_DIR,
}

afterEach(() => {
  for (const [key, value] of Object.entries(originalEnv)) {
    if (value === undefined) {
      delete process.env[key]
    } else {
      process.env[key] = value
    }
  }
})

describe("Control Center evidence config", () => {
  it("resolves default relative evidence paths from the repository root", () => {
    for (const key of Object.keys(originalEnv)) {
      delete process.env[key]
    }

    const config = getControlCenterEvidenceConfig()
    const repoRoot = path.dirname(process.cwd())

    expect(config.releasesDir).toBe(path.join(repoRoot, "releases", "evidence"))
    expect(config.qualityPath).toBe(path.join(repoRoot, "runtime", "repo-hygiene", "local-pr-quality.json"))
    expect(config.costReportPath).toBe(path.join(repoRoot, "runtime", "api-cost", "latest.json"))
    expect(config.actionAuditPath).toBe(path.join(repoRoot, "runtime", "control-center", "action-audit.jsonl"))
    expect(config.evidenceJsonPath).toBe(path.join(repoRoot, "runtime", "evidence", "latest.json"))
    expect(config.evidenceMarkdownPath).toBe(path.join(repoRoot, "runtime", "evidence", "latest.md"))
    expect(config.apiCostMarkdownPath).toBe(path.join(repoRoot, "runtime", "api-cost", "latest.md"))
  })

  it("uses configured paths for evidence collection", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-evidence-"))
    const releasesDir = path.join(root, "custom", "releases", "evidence")
    const sprintDir = path.join(releasesDir, "sprint-100")
    const qualityPath = path.join(root, "custom", "runtime", "repo-hygiene", "local-pr-quality.json")
    const costReportPath = path.join(root, "custom", "runtime", "api-cost", "latest.json")
    const costMarkdownPath = path.join(root, "custom", "runtime", "api-cost", "latest.md")
    const auditPath = path.join(root, "custom", "runtime", "control-center", "action-audit.jsonl")
    const datasetPath = path.join(root, "custom", "evals", "dataset.jsonl")
    const promptVariantsDir = path.join(root, "custom", "evals", "prompt-variants")

    await mkdir(sprintDir, { recursive: true })
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costReportPath), { recursive: true })
    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(path.dirname(datasetPath), { recursive: true })
    await mkdir(promptVariantsDir, { recursive: true })

    await writeFile(path.join(sprintDir, "CTOA-100.md"), "# Evidence\n", "utf-8")
    await writeFile(
      qualityPath,
      JSON.stringify({ status: "PASS", finding_count: 0, summary: { private_count: 0, public_count: 0, review_count: 0 } }),
      "utf-8",
    )
    await writeFile(costReportPath, JSON.stringify({ records_seen: 1, total_tokens: 10, total_cost_usd: 0.1 }), "utf-8")
    await writeFile(auditPath, '{"ok":true}\n', "utf-8")
    await writeFile(datasetPath, '{"case_id":"case-1","category":"custom","priority":"low"}\n', "utf-8")
    await writeFile(path.join(promptVariantsDir, "baseline.md"), "# baseline\n", "utf-8")

    process.env.CTOA_RELEASES_DIR = releasesDir
    process.env.CTOA_REPO_HYGIENE_PATH = qualityPath
    process.env.CTOA_API_COST_REPORT_PATH = costReportPath
    process.env.CTOA_API_COST_MD_OUT = costMarkdownPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_EVAL_DATASET_PATH = datasetPath
    process.env.CTOA_PROMPT_VARIANTS_DIR = promptVariantsDir

    const config = getControlCenterEvidenceConfig()
    const evidence = await collectControlCenterEvidence()

    expect(config.releasesDir).toBe(releasesDir)
    expect(config.qualityPath).toBe(qualityPath)
    expect(config.costReportPath).toBe(costReportPath)
    expect(config.apiCostMarkdownPath).toBe(costMarkdownPath)
    expect(config.actionAuditPath).toBe(auditPath)
    expect(config.evalDatasetPath).toBe(datasetPath)
    expect(config.promptVariantsDir).toBe(promptVariantsDir)
    expect(evidence.config.costReportPath).toBe(costReportPath)
    expect(evidence.releaseEvidenceFileCount).toBe(1)
    expect(evidence.repoHygiene.status).toBe("PASS")
    expect(evidence.apiCostReport.status).toBe("ready")
    expect(evidence.controlCenterAudit.recordCount).toBe(1)
    expect(evidence.latestReleaseEvidence?.path).toContain("CTOA-100.md")
  })
})
