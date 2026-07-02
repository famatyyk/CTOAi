import path from "node:path"

export type ControlCenterEvidenceConfig = {
  releasesDir: string
  qualityPath: string
  costReportPath: string
  actionAuditPath: string
  evidenceJsonPath: string
  evidenceMarkdownPath: string
  apiCostMarkdownPath: string
  evalDatasetPath: string
  promptVariantsDir: string
}

function trimTrailingSeparators(value: string): string {
  return value.replace(/[\\/]+$/, "")
}

function getRepoRoot(): string {
  const configuredRoot = process.env.CTOA_REPO_ROOT?.trim()
  if (configuredRoot) return trimTrailingSeparators(configuredRoot)

  const cwd = process.cwd()
  return path.basename(cwd) === "web" ? path.dirname(cwd) : cwd
}

function resolveConfiguredPath(value: string): string {
  const trimmed = trimTrailingSeparators(value)
  return path.isAbsolute(trimmed) ? trimmed : path.join(getRepoRoot(), trimmed)
}

function configuredPath(envName: string, fallback: string): string {
  return configuredPathFrom([envName], fallback)
}

function configuredPathFrom(envNames: string[], fallback: string): string {
  for (const envName of envNames) {
    const value = process.env[envName]?.trim()
    if (value) return resolveConfiguredPath(value)
  }

  return resolveConfiguredPath(fallback)
}

export function getControlCenterEvidenceConfig(): ControlCenterEvidenceConfig {
  return {
    releasesDir: configuredPath("CTOA_RELEASES_DIR", "releases/evidence"),
    qualityPath: configuredPath("CTOA_REPO_HYGIENE_PATH", "runtime/repo-hygiene/local-pr-quality.json"),
    costReportPath: configuredPath("CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json"),
    actionAuditPath: configuredPath("CTOA_ACTION_AUDIT_PATH", "runtime/control-center/action-audit.jsonl"),
    evidenceJsonPath: configuredPath("CTOA_EVIDENCE_JSON_PATH", "runtime/evidence/latest.json"),
    evidenceMarkdownPath: configuredPath("CTOA_EVIDENCE_MD_PATH", "runtime/evidence/latest.md"),
    apiCostMarkdownPath: configuredPathFrom(["CTOA_API_COST_MD_OUT", "CTOA_API_COST_MD_PATH"], "runtime/api-cost/latest.md"),
    evalDatasetPath: configuredPath(
      "CTOA_EVAL_DATASET_PATH",
      "evals/azure-activity-agent-eval-dataset.template.jsonl",
    ),
    promptVariantsDir: configuredPath("CTOA_PROMPT_VARIANTS_DIR", "evals/prompt-variants"),
  }
}
