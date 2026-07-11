import path from "node:path"

export type ControlCenterEvidenceConfig = {
  releasesDir: string
  qualityPath: string
  costReportPath: string
  actionAuditPath: string
  helperDevDir: string
  helperManifestPath: string
  helperValidationPath: string
  helperReleaseReadinessPath: string
  helperReleaseGatePath: string
  helperGoalStatusPath: string
  helperSmokePreflightPath: string
  helperSmokeStatusPath: string
  helperLivePromotionPath: string
  helperBackgroundStatusPath: string
  helperConditionsShadowReplayPath: string
  engineBrainManifestPath: string
  engineBrainP6ReadinessPath: string
  engineBrainP6PluginHandoffSmokePath: string
  engineBrainPackManifestPath: string
  engineBrainOwnershipMapPath: string
  engineBrainDocSyncPath: string
  engineBrainSecretGuardrailPath: string
  engineBrainOperatorBriefPath: string
  engineBrainP7CockpitSmokePath: string
  engineBrainP7SafeWriteDryRunSmokePath: string
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
  const helperDevDir = configuredPath("CTOA_HELPER_DEV_DIR", "runtime/solteria_helper_dev")
  return {
    releasesDir: configuredPath("CTOA_RELEASES_DIR", "releases/evidence"),
    qualityPath: configuredPath("CTOA_REPO_HYGIENE_PATH", "runtime/repo-hygiene/local-pr-quality.json"),
    costReportPath: configuredPath("CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json"),
    actionAuditPath: configuredPath("CTOA_ACTION_AUDIT_PATH", "runtime/control-center/action-audit.jsonl"),
    helperDevDir,
    helperManifestPath: configuredPath("CTOA_HELPER_MANIFEST_PATH", path.join(helperDevDir, "manifest.json")),
    helperValidationPath: configuredPath("CTOA_HELPER_VALIDATION_PATH", path.join(helperDevDir, "validation.json")),
    helperReleaseReadinessPath: configuredPath("CTOA_HELPER_RELEASE_READINESS_PATH", path.join(helperDevDir, "release_readiness.json")),
    helperReleaseGatePath: configuredPath("CTOA_HELPER_RELEASE_GATE_PATH", path.join(helperDevDir, "release_gate.json")),
    helperGoalStatusPath: configuredPath("CTOA_HELPER_GOAL_STATUS_PATH", path.join(helperDevDir, "goal_status.json")),
    helperSmokePreflightPath: configuredPath("CTOA_HELPER_SMOKE_PREFLIGHT_PATH", path.join(helperDevDir, "smoke_preflight.json")),
    helperSmokeStatusPath: configuredPath("CTOA_HELPER_SMOKE_STATUS_PATH", path.join(helperDevDir, "smoke_status.json")),
    helperLivePromotionPath: configuredPath("CTOA_HELPER_LIVE_PROMOTION_PATH", path.join(helperDevDir, "live_promotion.json")),
    helperBackgroundStatusPath: configuredPath(
      "CTOA_HELPER_BACKGROUND_STATUS_PATH",
      path.join(helperDevDir, "background_status.json"),
    ),
    helperConditionsShadowReplayPath: configuredPath(
      "CTOA_HELPER_CONDITIONS_SHADOW_REPLAY_PATH",
      path.join(helperDevDir, "conditions_shadow_replay.json"),
    ),
    engineBrainManifestPath: configuredPath("CTOA_ENGINE_BRAIN_MANIFEST_PATH", "AI/generated/manifest.json"),
    engineBrainP6ReadinessPath: configuredPath("CTOA_ENGINE_BRAIN_P6_READINESS_PATH", "AI/generated/P6_CODEX_INTEGRATION_READINESS.json"),
    engineBrainP6PluginHandoffSmokePath: configuredPath(
      "CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH",
      "runtime/control-center/p6-plugin-handoff-smoke.json",
    ),
    engineBrainPackManifestPath: configuredPath("CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH", "AI/generated/ENGINE_BRAIN_PACK.json"),
    engineBrainOwnershipMapPath: configuredPath("CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH", "AI/generated/OWNERSHIP_MAP.md"),
    engineBrainDocSyncPath: configuredPath("CTOA_ENGINE_BRAIN_DOC_SYNC_PATH", "AI/generated/DOC_SYNC.json"),
    engineBrainSecretGuardrailPath: configuredPath("CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH", "AI/generated/SECRET_GUARDRAIL.json"),
    engineBrainOperatorBriefPath: configuredPath("CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH", "AI/generated/P7_OPERATOR_BRIEF.json"),
    engineBrainP7CockpitSmokePath: configuredPath("CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH", "runtime/control-center/p7-cockpit-smoke.json"),
    engineBrainP7SafeWriteDryRunSmokePath: configuredPath(
      "CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH",
      "runtime/control-center/p7-safe-write-dry-run-smoke.json",
    ),
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
