import { lstat, open, readdir, readFile, stat } from "node:fs/promises"
import crypto from "node:crypto"
import path from "node:path"
import { toControlCenterDisplayConfig, toControlCenterDisplayPath } from "@/lib/controlCenterDisplayPath"
import { getControlCenterEvidenceConfig, type ControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { sanitizeControlCenterDisplayText } from "@/lib/controlCenterRedaction"

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
  releaseEvidenceDrilldown: {
    status: string
    root: string
    fileCount: number
    sprintCount: number
    latestSprint: string
    latestModifiedAt: string
    recentFiles: Array<{
      sprint: string
      path: string
      title: string
      modifiedAt: string
      bytes: number
    }>
    nextAction: string
  }
  releaseComparison: {
    status: string
    relation: string
    currentJsonPath: string
    currentMarkdownPath: string
    currentGeneratedAt: string
    currentModifiedAt: string
    currentExists: boolean
    trackedPath: string
    trackedModifiedAt: string
    trackedExists: boolean
    minutesBetween: number | null
    nextAction: string
    nextCommand: string
  }
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
  actionAuditDrilldown: {
    status: string
    path: string
    recordCount: number
    invalidRecordCount: number
    truncated: boolean
    sourceBytes: number
    sampledBytes: number
    latestAt: string
    actionCounts: Record<string, number>
    riskCounts: Record<string, number>
    authorizedCount: number
    deniedCount: number
    dryRunCount: number
    failedCount: number
    recentRecords: Array<{
      at: string
      auditId: string
      action: string
      target: string
      riskClass: string
      actorRole: string
      authorized: string
      ok: string
      dryRun: boolean
      summary: string
    }>
    nextAction: string
    nextCommand: string
  }
  otclientHelper: {
    status: string
    helperVersion: string
    manifestHash: string
    validationStatus: string
    releaseReadinessStatus: string
    releaseGateStatus: string
    releasableToLive: boolean
    smokePreflightStatus: string
    smokeStatus: string
    livePromotionStatus: string
    livePromoted: boolean
    livePromotionCreatedAt: string
    liveClient: string
    liveBackupPath: string
    stagedFileCount: number
    packagePath: string
    packageSha256: string
    blockers: string[]
    backgroundStatus: {
      status: string
      reportedStatus: string
      mode: string
      generatedAt: string
      maxAgeSeconds: number
      ageSeconds: number | null
      fresh: boolean
      contractValid: boolean
      contractErrors: string[]
      advisoryOnly: boolean
      safeToRunWhilePlaying: boolean
      promotionAllowed: boolean
      dispatchAllowed: boolean
      runtimeActions: boolean
      processState: string
      integrityStatus: string
      pinErrors: string[]
      pinClassification: string
      pinRequiredAction: string
      pinHistoricalRebindingAllowed: boolean
      pinRequiresExplicitLiveApproval: boolean
      diagnosticParityStatus: string
      diagnosticParityAttempted: boolean
      diagnosticProfileDriftCount: number
      diagnosticStableDuringObservation: boolean
      diagnosticAcceptanceAllowed: boolean
      matchedFileCount: number
      manifestFileCount: number
      mutableDriftCount: number
      capabilityStatus: string
      capabilityFresh: boolean
      runtimeState: string
      blockers: string[]
    }
    conditionsShadowReplay: {
      status: string
      reportedStatus: string
      generatedAtUnixMs: number | null
      maxAgeSeconds: number
      ageSeconds: number | null
      fresh: boolean
      contractValid: boolean
      contractErrors: string[]
      scenarioPackStatus: string
      fixtureOnlyValidationPassed: boolean
      runtimeReadinessClaimed: boolean
      traceStatus: string
      decision: string
      decisionSha256: string
      scenarioTotalCount: number
      scenarioPassedCount: number
      scenarioFailedCount: number
      blockers: string[]
      dispatchAllowed: boolean
      runtimeActions: boolean
      executesPlan: boolean
      executeOnceAllowed: boolean
      promotionAllowed: boolean
    }
    nextAction: string
    nextCommand: string
    sourcePaths: {
      devDir: string
      manifest: string
      validation: string
      releaseReadiness: string
      releaseGate: string
      goalStatus: string
      smokePreflight: string
      smokeStatus: string
      livePromotion: string
      backgroundStatus: string
      conditionsShadowReplay: string
    }
  }
  engineBrain: {
    status: string
    generatedAt: string
    fileCount: number
    docSyncStatus: string
    secretGuardrailStatus: string
    p6ReadinessStatus: string
    p6PluginHandoff: {
      status: string
      policy: string
      recommendedNext: string
      checkCount: number
      passedCheckCount: number
      marketplaceStatus: string
      installedCacheStatus: string
      installedCacheVersion: string
      mcpContractCount: number
      passedMcpContractCount: number
      freshThreadRequired: boolean
      smokeStatus: string
      smokeGeneratedAt: string
      smokeCheckCount: number
      smokePassedCount: number
      smokeBlockedCount: number
      currentThreadToolDiscoveryStatus: string
      freshThreadVerificationStatus: string
      freshThreadRecommendedToolOrder: string[]
      smokeNextAction: string
      smokeSourcePath: string
      nextAction: string
      sourcePath: string
    }
    p7OperatorBriefStatus: string
    p7Decision: string
    p7GeneratedAt: string
    p7HardBlockerCount: number
    p7WarningCount: number
    p7Warnings: string[]
    p7NextSafeCommand: string
    p7Policy: string
    p7RoadmapGenerationStatus: string
    p7RoadmapGenerationDocSyncStatus: string
    p7RoadmapGenerationDocCount: number
    p7RoadmapGenerationReadyDocCount: number
    p7RoadmapGenerationHardBlockerCount: number
    p7RoadmapGenerationNextAction: string
    p7RoadmapGenerationBlockedUntil: string
    p7ActionReadinessStatus: string
    p7ActionReadinessDecision: string
    p7ActionCandidateCount: number
    p7ActionAuditedCandidateCount: number
    p7McpWriteToolCount: number
    p7EnabledSafeWriteToolCount: number
    p7ReadySafeWriteAuditCount: number
    p7SafeWriteAuditCount: number
    p7OperatorCockpitSummary: string
    p7EnabledSafeWriteTools: Array<{
      actionId: string
      mcpTool: string
      riskClass: string
      auditStatus: string
    }>
    p7ActionNextSafeMode: string
    p7ActionNextSafeCommand: string
    p7SafeWriteToolDesignStatus: string
    p7SafeWriteToolDesignDecision: string
    p7SafeWriteToolSelectedActionId: string
    p7SafeWriteToolProposedMcpTool: string
    p7SafeWriteToolRiskClass: string
    p7SafeWriteToolMode: string
    p7SafeWriteToolMcpEnabled: boolean
    p7SafeWriteToolNextSafeCommand: string
    p7SafeWriteAudit: {
      status: string
      expectedAction: string
      proposedMcpTool: string
      auditId: string
      latestAt: string
      riskClass: string
      actorRole: string
      authorized: string
      ok: string
      dryRun: boolean
      summary: string
      nextAction: string
    }
    p7SafeWriteAudits: Array<{
      status: string
      expectedAction: string
      proposedMcpTool: string
      auditId: string
      latestAt: string
      riskClass: string
      actorRole: string
      authorized: string
      ok: string
      dryRun: boolean
      summary: string
      nextAction: string
    }>
    p7CockpitSmoke: {
      status: string
      generatedAt: string
      checkCount: number
      passedCount: number
      blockedCount: number
      enabledSafeWriteToolCount: number
      readySafeWriteAuditCount: number
      expectedSafeWriteAuditCount: number
      actionAuditLineCount: number
      hardBlockers: string[]
      warnings: string[]
      nextAction: string
      sourcePath: string
    }
    p7SafeWriteDryRunSmoke: {
      status: string
      generatedAt: string
      checkCount: number
      passedCount: number
      blockedCount: number
      safeWriteToolCount: number
      dryRunReadyCount: number
      preflightReadyCount: number
      bootstrapAllowedCount: number
      hardBlockers: string[]
      warnings: string[]
      results: Array<{
        actionId: string
        mcpTool: string
        status: string
        auditRecordReady: boolean
        preflightOk: boolean
        preflightBootstrapAllowed: boolean
      }>
      nextAction: string
      sourcePath: string
    }
    packProfile: string
    packIncludedCount: number
    packTruncatedCount: number
    packGeneratedAt: string
    sourcePaths: {
      manifest: string
      p6Readiness: string
      p6PluginHandoffSmoke: string
      packManifest: string
      ownershipMap: string
      docSync: string
      secretGuardrail: string
      operatorBrief: string
      p7CockpitSmoke: string
      p7SafeWriteDryRunSmoke: string
    }
    nextAction: string
    nextCommand: string
  }
  artifactHealth: {
    status: string
    staleCount: number
    blockedCount: number
    checks: Array<{
      name: string
      status: string
      detail: string
      artifactPath: string
      ageMinutes: number | null
    }>
    nextAction: string
    nextCommand: string
  }
  operatorBrief: {
    status: string
    decision: string
    generatedAt: string
    ready: boolean
    hardBlockerCount: number
    warningCount: number
    policy: string
    nextSafeCommand: string
    sourcePath: string
    roadmapGeneration: {
      status: string
      docSyncStatus: string
      docCount: number
      readyDocCount: number
      hardBlockerCount: number
      nextAction: string
      blockedUntil: string
    }
    cockpitHandoff: {
      status: string
      ready: boolean
      hardBlockerCount: number
      warningCount: number
      recommendedToolOrder: string[]
      p7Cockpit: {
        status: string
        enabledSafeWriteToolCount: number
        readyAuditCount: number
        auditCount: number
        mcpWriteToolCount: number
      }
      p7CockpitSmoke: {
        status: string
        checks: number
        passed: number
        blocked: number
        actionAuditLineCount: number
      }
      p7SafeWriteDryRunSmoke: {
        status: string
        checks: number
        passed: number
        blocked: number
        safeWriteToolCount: number
        dryRunReadyCount: number
        preflightReadyCount: number
        bootstrapAllowedCount: number
      }
      releaseEvidence: {
        status: string
        fileCount: number
        sprintCount: number
        latestPath: string
      }
      actionAudit: {
        status: string
        recordCount: number
        latestAt: string
        invalidRecordCount: number
        riskCounts: Record<string, number>
      }
    }
  }
  operatorNext: {
    status: string
    lane: string
    riskClass: string
    title: string
    detail: string
    command: string
    sourcePath: string
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

const FRESH_ARTIFACT_MAX_AGE_MINUTES = 24 * 60
const CONTROL_CENTER_EVIDENCE_JSON_MAX_BYTES = 1024 * 1024
const CONTROL_CENTER_MARKDOWN_TITLE_MAX_BYTES = 64 * 1024
export const CONTROL_CENTER_ACTION_AUDIT_MAX_BYTES = 1024 * 1024
const ACTION_AUDIT_MAX_LINE_LENGTH = 20 * 1024
const BACKGROUND_STATUS_SCHEMA = "ctoa.otclient-headless-status.v1"
const BACKGROUND_STATUS_MODE = "background_no_screen"
const BACKGROUND_STATUS_MAX_AGE_MS = 30_000
const BACKGROUND_STATUS_VALUES = new Set([
  "ready",
  "blocked",
  "idle",
  "waiting_for_passive_heartbeat",
  "observation_pending",
])
const BACKGROUND_INTEGRITY_STATUS_VALUES = new Set(["passed", "failed", "untrusted_pin"])
const BACKGROUND_PIN_CLASSIFICATION_VALUES = new Set([
  "trusted",
  "missing_or_unreadable_attestation",
  "legacy_or_unbound_attestation",
  "invalid_or_mismatched_attestation",
])
const BACKGROUND_PIN_REQUIRED_ACTION_VALUES = new Set([
  "none",
  "refresh_official_live_promotion_after_current_gates",
])
const BACKGROUND_DIAGNOSTIC_STATUS_VALUES = new Set(["not_required", "unavailable", "passed", "failed"])
const BACKGROUND_PIN_ERROR_VALUES = new Set([
  "live_manifest_schema_invalid",
  "live_manifest_origin_invalid",
  "live_manifest_timestamp_invalid",
  "live_manifest_helper_version_invalid",
  "manifest_files_missing",
  "manifest_entry_limit_exceeded",
  "manifest_total_bytes_exceeded",
  "live_promotion_name_invalid",
  "live_promotion_approval_invalid",
  "live_promotion_verification_invalid",
  "live_promotion_helper_version_mismatch",
  "live_promotion_file_count_mismatch",
  "live_promotion_manifest_path_mismatch",
  "live_promotion_manifest_sha256_mismatch",
  "live_promotion_client_path_mismatch",
  "live_promotion_timestamp_mismatch",
])
const BACKGROUND_CAPABILITY_STATUS_VALUES = new Set([
  "fresh",
  "stale",
  "missing",
  "unsafe_runtime_claim",
  "schema_mismatch",
  "invalid_contract",
  "version_mismatch",
  "invalid_heartbeat",
  "heartbeat_before_process",
  "heartbeat_offline",
  "game_offline",
  "malformed",
  "oversize",
  "symlink_rejected",
  "not_regular",
  "not_object",
  "changed_during_open",
  "unreadable",
  "explicit_path_mismatch",
])
const BACKGROUND_BLOCKER_VALUES = new Set([
  "live_manifest_pin_untrusted",
  "live_manifest_parity_failed",
  "live_files_changed_or_unverifiable",
  "active_client_process_count_invalid",
  "active_client_process_start_invalid",
  "current_session_lua_exception",
  "client_process_changed_during_observation",
  "screenshot_count_changed_during_observation",
  ...Array.from(BACKGROUND_CAPABILITY_STATUS_VALUES, (status) => `capability_${status}`),
])
const BACKGROUND_INTERACTION_CONTRACT: Record<string, unknown> = {
  gui_automation: false,
  mouse_keyboard_input: false,
  window_focus: false,
  screenshot_capture: false,
  client_launch: false,
  client_stop: false,
  live_file_writes: false,
  passive_reads_only: true,
  evidence_write_scope: "runtime/solteria_helper_dev",
}
const BACKGROUND_WRAPPER_INVARIANTS: Record<string, unknown> = {
  client_process_stable: true,
  screenshot_count_stable: true,
}
const CONDITIONS_SHADOW_REPORT_SCHEMA = "ctoa.conditions-shadow-replay-report.v1"
const CONDITIONS_SHADOW_TRACE_SCHEMA = "ctoa.conditions-shadow-trace.v1"
const CONDITIONS_SHADOW_INPUT_SCHEMA = "ctoa.conditions-shadow-input.v1"
const CONDITIONS_SHADOW_REPORT_MODE = "offline_shadow_replay"
const CONDITIONS_SHADOW_REPORT_MAX_AGE_MS = 30_000
const CONDITIONS_SHADOW_ACTION_FLAGS = [
  "dispatch_allowed",
  "runtime_actions",
  "executes_plan",
  "execute_once_allowed",
  "promotion_allowed",
] as const
const CONDITIONS_SHADOW_REPORT_KEYS = [
  "schema_version",
  "generated_at_unix_ms",
  "mode",
  "operational_acceptance_status",
  "scenario_pack_status",
  "fixture_only_validation_passed",
  "runtime_readiness_claimed",
  "operational_trace",
  "scenario_pack",
  ...CONDITIONS_SHADOW_ACTION_FLAGS,
  "intrusive_actions_performed",
] as const
const CONDITIONS_SHADOW_TRACE_KEYS = [
  "schema_version",
  "trace_id",
  "source",
  "evaluated_at_unix_ms",
  "mode",
  "action",
  "condition",
  "spell",
  "input_sha256",
  "canonical_input_sha256",
  "observation_age_ms",
  "p8_age_ms",
  "recovery_trace_age_ms",
  "recovery_age_ms",
  "status",
  "decision",
  "blockers",
  "decision_sha256",
  "operator_review_required",
  ...CONDITIONS_SHADOW_ACTION_FLAGS,
  "intrusive_actions_performed",
] as const
const CONDITIONS_SHADOW_SCENARIO_PACK_KEYS = [
  "status",
  "fixture_only",
  "operational_readiness_claimed",
  "scenario_pack_sha256",
  "total_count",
  "passed_count",
  "failed_count",
  "cases",
  ...CONDITIONS_SHADOW_ACTION_FLAGS,
  "intrusive_actions_performed",
] as const
const CONDITIONS_SHADOW_CASE_KEYS = [
  "name",
  "mutation",
  "expected_status",
  "actual_status",
  "expected_blockers",
  "blockers",
  "canonical_input_sha256",
  "decision_sha256",
  "deterministic",
  "passed",
  ...CONDITIONS_SHADOW_ACTION_FLAGS,
  "intrusive_actions_performed",
] as const
const CONDITIONS_SHADOW_INPUT_HASH_KEYS = [
  "profile",
  "observation",
  "p8_proof",
  "recovery_trace",
  "recovery_proof",
] as const
const CONDITIONS_SHADOW_BLOCKER_ORDER = [
  "profile_missing", "profile_malformed", "profile_duplicate_keys", "profile_oversize", "profile_symlink_rejected",
  "profile_not_regular", "profile_unreadable", "profile_schema_invalid", "profile_action_mismatch", "profile_condition_mismatch",
  "profile_spell_mismatch", "profile_cooldown_policy_invalid", "profile_retry_budget_nonzero", "profile_p8_proof_not_required",
  "profile_recovery_proof_not_required", "profile_unsafe_contract", "observation_missing", "observation_malformed",
  "observation_duplicate_keys", "observation_oversize", "observation_symlink_rejected", "observation_not_regular",
  "observation_unreadable", "observation_envelope_invalid", "observation_schema_invalid", "observation_future",
  "observation_stale", "player_offline", "player_online_unknown", "player_dead", "player_life_unknown",
  "protection_zone_inside", "protection_zone_unknown", "protection_zone_source_untrusted", "condition_mismatch",
  "condition_absent", "condition_unknown", "cooldown_active", "cooldown_unknown", "cooldown_source_untrusted",
  "observation_unsafe_contract", "p8_missing", "p8_malformed", "p8_duplicate_keys", "p8_oversize",
  "p8_symlink_rejected", "p8_not_regular", "p8_unreadable", "p8_schema_invalid", "p8_future", "p8_stale",
  "p8_observation_hash_mismatch", "p8_operational_acceptance_blocked", "p8_unsafe_contract", "recovery_trace_missing",
  "recovery_trace_malformed", "recovery_trace_duplicate_keys", "recovery_trace_oversize", "recovery_trace_symlink_rejected",
  "recovery_trace_not_regular", "recovery_trace_unreadable", "recovery_trace_schema_invalid", "recovery_trace_future",
  "recovery_trace_stale", "recovery_trace_status_blocked", "recovery_trace_action_mismatch", "recovery_trace_unsafe_contract",
  "recovery_missing", "recovery_malformed", "recovery_duplicate_keys", "recovery_oversize", "recovery_symlink_rejected",
  "recovery_not_regular", "recovery_unreadable", "recovery_schema_invalid", "recovery_future", "recovery_stale",
  "recovery_status_blocked", "recovery_action_mismatch", "recovery_condition_mismatch", "recovery_spell_mismatch",
  "recovery_trace_hash_mismatch", "recovery_profile_hash_mismatch", "recovery_observation_hash_mismatch",
  "recovery_p8_hash_mismatch", "recovery_unsafe_contract", "fixture_observation_not_operational",
  "fixture_p8_proof_not_operational", "fixture_recovery_trace_not_operational", "fixture_recovery_proof_not_operational",
] as const
const CONDITIONS_SHADOW_BLOCKER_RANK = new Map(CONDITIONS_SHADOW_BLOCKER_ORDER.map((value, index) => [value, index]))
const CONDITIONS_SHADOW_SCENARIO_MUTATIONS = new Set([
  "none",
  "profile_wrong_action",
  "profile_wrong_condition",
  "profile_wrong_spell",
  "profile_retry_nonzero",
  "profile_future_version",
  "profile_malformed",
  "profile_duplicate_keys",
  "profile_oversized",
  "profile_symlinked",
  "profile_non_regular",
  "profile_extra_field",
  "observation_stale",
  "observation_future",
  "player_offline",
  "player_online_unknown",
  "player_dead",
  "player_life_unknown",
  "protection_zone_inside",
  "protection_zone_unknown",
  "condition_absent",
  "condition_unknown",
  "condition_wrong",
  "cooldown_active",
  "cooldown_unknown",
  "observation_extra_field",
  "observation_unsafe_contract",
  "p8_missing",
  "p8_blocked",
  "p8_stale",
  "p8_future",
  "p8_unsafe_contract",
  "p8_extra_field",
  "recovery_missing",
  "recovery_malformed",
  "recovery_status_blocked",
  "recovery_future",
  "recovery_stale",
  "recovery_wrong_action",
  "recovery_wrong_condition",
  "recovery_wrong_spell",
  "recovery_hash_mismatch",
  "recovery_extra_field",
  "recovery_unsafe_contract",
])

export async function collectControlCenterEvidence(): Promise<ControlCenterEvidence> {
  const config = getControlCenterEvidenceConfig()
  const latestReleaseEvidence = await findLatestReleaseEvidence(config.releasesDir)
  const releaseEvidenceFileCount = await countMarkdownFiles(config.releasesDir)
  const releaseSprints = await listReleaseSprints(config.releasesDir)
  const releaseEvidenceDrilldown = await collectReleaseEvidenceDrilldown(config.releasesDir)
  const releaseComparison = await collectReleaseComparison(config, latestReleaseEvidence)
  const repoHygiene = await readJsonIfExists(config.qualityPath)
  const apiCostReport = await readJsonIfExists(config.costReportPath)
  const actionAuditDrilldown = await collectActionAuditDrilldown(config.actionAuditPath)
  const otclientHelper = await collectOtclientHelperStatus(config)
  const engineBrain = await collectEngineBrainStatus(config)
  const artifactHealth = await collectArtifactHealth(config, actionAuditDrilldown)
  const operatorBrief = await collectOperatorBriefCard(config)

  const recommendations: string[] = []
  const repoStatus = String(repoHygiene?.status || "missing")
  if (!repoHygiene) {
    recommendations.push("Run repo hygiene quality generation before sign-off.")
  } else if (repoStatus !== "PASS") {
    recommendations.push("Review repo hygiene findings before treating the pack as release-ready.")
  }

  if (!apiCostReport) {
    recommendations.push(`Generate ${toControlCenterDisplayPath(config.costReportPath)} with scripts/ops/api_cost_report.py.`)
  } else if (Number(apiCostReport.records_seen || 0) === 0) {
    recommendations.push("Cost report exists but has no records; verify eval artifacts in evals/runs.")
  }

  if (actionAuditDrilldown.recordCount === 0) {
    recommendations.push("Exercise at least one Control Center action so the audit trail is visible.")
  }

  if (otclientHelper.status === "missing") {
    recommendations.push("Prepare the Solteria Helper dev package before release review.")
  } else if (otclientHelper.status !== "releasable" && otclientHelper.status !== "promoted") {
    recommendations.push(otclientHelper.nextAction || "Refresh Solteria Helper validation and release gate evidence.")
  }

  if (engineBrain.status === "missing") {
    recommendations.push("Run .\\ctoa.ps1 brain refresh before treating Engine Brain context as current.")
  } else if (engineBrain.status !== "ready") {
    recommendations.push(engineBrain.nextAction)
  }

  if (artifactHealth.status !== "ready") {
    recommendations.push(artifactHealth.nextAction)
  }

  if (recommendations.length === 0) {
    recommendations.push("Evidence pack is ready for review. Keep fresh traces attached to the release note.")
  }
  const operatorNext = buildOperatorNextRecommendation({
    repoStatus,
    apiCostReport,
    actionAuditDrilldown,
    otclientHelper,
    engineBrain,
    artifactHealth,
    config,
  })

  const evalArtifacts = (apiCostReport?.eval_artifacts as ApiCostReportArtifact | undefined) || {}

  return {
    generatedAt: new Date().toISOString(),
    config: toControlCenterDisplayConfig(config),
    latestReleaseEvidence: latestReleaseEvidence
      ? {
          ...latestReleaseEvidence,
          path: toControlCenterDisplayPath(latestReleaseEvidence.path),
        }
      : null,
    releaseEvidenceFileCount,
    releaseSprints,
    releaseEvidenceDrilldown,
    releaseComparison,
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
        datasetPath: toControlCenterDisplayPath(
          String(evalArtifacts.dataset_path || "evals/azure-activity-agent-eval-dataset.template.jsonl"),
        ),
        datasetCases: Number(evalArtifacts.dataset_cases || 0),
        categoryCounts: evalArtifacts.category_counts || {},
        priorityCounts: evalArtifacts.priority_counts || {},
        promptVariantsDir: toControlCenterDisplayPath(String(evalArtifacts.prompt_variants_dir || "evals/prompt-variants")),
        promptVariantCount: Number(evalArtifacts.prompt_variant_count || 0),
        promptVariants: evalArtifacts.prompt_variants || [],
      },
    },
    controlCenterAudit: {
      status: actionAuditDrilldown.recordCount ? "ready" : "missing",
      recordCount: actionAuditDrilldown.recordCount,
    },
    actionAuditDrilldown,
    otclientHelper,
    engineBrain,
    artifactHealth,
    operatorBrief,
    operatorNext,
    recommendations,
  }
}

async function collectOperatorBriefCard(
  config: ControlCenterEvidenceConfig,
): Promise<ControlCenterEvidence["operatorBrief"]> {
  const payload = await readJsonIfExists(config.engineBrainOperatorBriefPath)
  const cockpitHandoff: Record<string, unknown> = isRecord(payload?.cockpit_handoff) ? payload.cockpit_handoff : {}
  const p7Cockpit: Record<string, unknown> = isRecord(cockpitHandoff.p7_cockpit) ? cockpitHandoff.p7_cockpit : {}
  const p7CockpitSmoke: Record<string, unknown> = isRecord(cockpitHandoff.p7_cockpit_smoke) ? cockpitHandoff.p7_cockpit_smoke : {}
  const p7SafeWriteDryRunSmoke: Record<string, unknown> = isRecord(cockpitHandoff.p7_safe_write_dry_run_smoke)
    ? cockpitHandoff.p7_safe_write_dry_run_smoke
    : {}
  const releaseEvidence: Record<string, unknown> = isRecord(cockpitHandoff.release_evidence) ? cockpitHandoff.release_evidence : {}
  const actionAudit: Record<string, unknown> = isRecord(cockpitHandoff.action_audit) ? cockpitHandoff.action_audit : {}
  const roadmapGeneration: Record<string, unknown> = isRecord(payload?.roadmap_generation) ? payload.roadmap_generation : {}
  const hardBlockers = Array.isArray(payload?.hard_blockers) ? payload.hard_blockers : []
  const warnings = Array.isArray(payload?.warnings) ? payload.warnings : []
  const roadmapHardBlockers = Array.isArray(roadmapGeneration.hard_blockers) ? roadmapGeneration.hard_blockers : []
  const handoffBlockers = Array.isArray(cockpitHandoff.hard_blockers) ? cockpitHandoff.hard_blockers : []
  const handoffWarnings = Array.isArray(cockpitHandoff.warnings) ? cockpitHandoff.warnings : []
  const recommendedToolOrder = Array.isArray(cockpitHandoff.recommended_tool_order)
    ? cockpitHandoff.recommended_tool_order.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 6)
    : []
  const ready = payload !== null && String(payload.status || "missing") === "ready" && cockpitHandoff.ready === true

  return {
    status: payload ? sanitizeText(String(payload.status || "missing"), 80) : "missing",
    decision: sanitizeText(String(payload?.decision || ""), 120),
    generatedAt: String(payload?.generated_at || ""),
    ready,
    hardBlockerCount: hardBlockers.length,
    warningCount: warnings.length,
    policy: sanitizeText(String(payload?.policy || ""), 220),
    nextSafeCommand: sanitizeText(String(payload?.next_safe_command || ""), 220),
    sourcePath: toControlCenterDisplayPath(config.engineBrainOperatorBriefPath),
    roadmapGeneration: {
      status: sanitizeText(String(roadmapGeneration.status || "missing"), 80),
      docSyncStatus: sanitizeText(String(roadmapGeneration.doc_sync_status || "missing"), 80),
      docCount: Number(roadmapGeneration.doc_count || 0),
      readyDocCount: Number(roadmapGeneration.ready_doc_count || 0),
      hardBlockerCount: roadmapHardBlockers.length,
      nextAction: sanitizeText(String(roadmapGeneration.next_action || ""), 180),
      blockedUntil: sanitizeText(String(roadmapGeneration.blocked_until || ""), 180),
    },
    cockpitHandoff: {
      status: sanitizeText(String(cockpitHandoff.status || "missing"), 80),
      ready: cockpitHandoff.ready === true,
      hardBlockerCount: handoffBlockers.length,
      warningCount: handoffWarnings.length,
      recommendedToolOrder,
      p7Cockpit: {
        status: sanitizeText(String(p7Cockpit.status || "missing"), 80),
        enabledSafeWriteToolCount: Number(p7Cockpit.enabled_safe_write_tool_count || 0),
        readyAuditCount: Number(p7Cockpit.ready_audit_count || 0),
        auditCount: Number(p7Cockpit.audit_count || 0),
        mcpWriteToolCount: Number(p7Cockpit.mcp_write_tool_count || 0),
      },
      p7CockpitSmoke: {
        status: sanitizeText(String(p7CockpitSmoke.status || "missing"), 80),
        checks: Number(p7CockpitSmoke.checks || 0),
        passed: Number(p7CockpitSmoke.passed || 0),
        blocked: Number(p7CockpitSmoke.blocked || 0),
        actionAuditLineCount: Number(p7CockpitSmoke.action_audit_line_count || 0),
      },
      p7SafeWriteDryRunSmoke: {
        status: sanitizeText(String(p7SafeWriteDryRunSmoke.status || "missing"), 80),
        checks: Number(p7SafeWriteDryRunSmoke.checks || 0),
        passed: Number(p7SafeWriteDryRunSmoke.passed || 0),
        blocked: Number(p7SafeWriteDryRunSmoke.blocked || 0),
        safeWriteToolCount: Number(p7SafeWriteDryRunSmoke.safe_write_tool_count || 0),
        dryRunReadyCount: Number(p7SafeWriteDryRunSmoke.dry_run_ready_count || 0),
        preflightReadyCount: Number(p7SafeWriteDryRunSmoke.preflight_ready_count || 0),
        bootstrapAllowedCount: Number(p7SafeWriteDryRunSmoke.bootstrap_allowed_count || 0),
      },
      releaseEvidence: {
        status: sanitizeText(String(releaseEvidence.status || "missing"), 80),
        fileCount: Number(releaseEvidence.file_count || 0),
        sprintCount: Number(releaseEvidence.sprint_count || 0),
        latestPath: toControlCenterDisplayPath(String(releaseEvidence.latest_path || "")),
      },
      actionAudit: {
        status: sanitizeText(String(actionAudit.status || "missing"), 80),
        recordCount: Number(actionAudit.record_count || 0),
        latestAt: String(actionAudit.latest_at || ""),
        invalidRecordCount: Number(actionAudit.invalid_record_count || 0),
        riskCounts: sanitizeCountMap(actionAudit.risk_counts),
      },
    },
  }
}

function buildOperatorNextRecommendation({
  repoStatus,
  apiCostReport,
  actionAuditDrilldown,
  otclientHelper,
  engineBrain,
  artifactHealth,
  config,
}: {
  repoStatus: string
  apiCostReport: Record<string, unknown> | null
  actionAuditDrilldown: ControlCenterEvidence["actionAuditDrilldown"]
  otclientHelper: ControlCenterEvidence["otclientHelper"]
  engineBrain: ControlCenterEvidence["engineBrain"]
  artifactHealth: ControlCenterEvidence["artifactHealth"]
  config: ControlCenterEvidenceConfig
}): ControlCenterEvidence["operatorNext"] {
  const safeCommand = (command: string) => (isGuardedLiveCommand(command) ? "" : sanitizeText(command, 220))
  const artifactProblem = artifactHealth.checks.find((check) => check.status !== "passed")

  if (engineBrain.status === "missing" || engineBrain.status === "blocked") {
    return {
      status: engineBrain.status === "blocked" ? "blocked" : "warn",
      lane: "engine-brain",
      riskClass: "read_only",
      title: "Refresh Engine Brain context",
      detail: sanitizeText(engineBrain.nextAction || "Regenerate Engine Brain evidence before operator work continues.", 220),
      command: safeCommand(engineBrain.nextCommand || ".\\ctoa.ps1 brain refresh"),
      sourcePath: engineBrain.sourcePaths.manifest,
    }
  }

  if (engineBrain.p7CockpitSmoke.status !== "ready" || engineBrain.p7CockpitSmoke.blockedCount > 0) {
    return {
      status: "blocked",
      lane: "p7-cockpit-smoke",
      riskClass: "read_only",
      title: "Refresh P7 cockpit smoke",
      detail: sanitizeText(engineBrain.p7CockpitSmoke.nextAction, 220),
      command: ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_cockpit_smoke.py",
      sourcePath: engineBrain.p7CockpitSmoke.sourcePath,
    }
  }

  if (
    engineBrain.p7SafeWriteDryRunSmoke.status !== "ready" ||
    engineBrain.p7SafeWriteDryRunSmoke.blockedCount > 0 ||
    engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount === 0 ||
    engineBrain.p7SafeWriteDryRunSmoke.dryRunReadyCount !== engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount ||
    engineBrain.p7SafeWriteDryRunSmoke.preflightReadyCount !== engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount ||
    engineBrain.p7SafeWriteDryRunSmoke.bootstrapAllowedCount !== 0
  ) {
    return {
      status: "blocked",
      lane: "p7-safe-write-dry-run-smoke",
      riskClass: "read_only",
      title: "Refresh P7 safe-write dry-run smoke",
      detail: sanitizeText(engineBrain.p7SafeWriteDryRunSmoke.nextAction, 220),
      command: ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_safe_write_dry_run_smoke.py",
      sourcePath: engineBrain.p7SafeWriteDryRunSmoke.sourcePath,
    }
  }

  if (engineBrain.p7EnabledSafeWriteToolCount > 0 && engineBrain.p7ReadySafeWriteAuditCount < engineBrain.p7SafeWriteAuditCount) {
    return {
      status: "warn",
      lane: "p7-action-audit",
      riskClass: "safe_write",
      title: "Collect P7 safe-write audit evidence",
      detail: sanitizeText(engineBrain.p7SafeWriteAudit.nextAction, 220),
      command: safeCommand(engineBrain.p7SafeWriteToolNextSafeCommand || engineBrain.p7ActionNextSafeCommand),
      sourcePath: toControlCenterDisplayPath(config.actionAuditPath),
    }
  }

  if (actionAuditDrilldown.recordCount === 0 || actionAuditDrilldown.truncated) {
    return {
      status: actionAuditDrilldown.recordCount === 0 ? "warn" : "blocked",
      lane: "control-center-audit",
      riskClass: "read_only",
      title: "Refresh Control Center audit evidence",
      detail: sanitizeText(actionAuditDrilldown.nextAction, 220),
      command: safeCommand(actionAuditDrilldown.nextCommand),
      sourcePath: actionAuditDrilldown.path,
    }
  }

  if (engineBrain.p7ActionReadinessStatus === "safe_write_tools_enabled" && engineBrain.p7ActionNextSafeCommand) {
    const designNext = engineBrain.p7ActionNextSafeMode === "design_next_p7_plugin_action"
    const reviewConfirmed = engineBrain.p7ActionNextSafeMode === "review_confirmed_safe_write_evidence"
    const confirmedSafeWrite = /\bdry_run=false\b/.test(engineBrain.p7ActionNextSafeCommand)
    return {
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: designNext
        ? "Design next P7 plugin action"
        : reviewConfirmed
        ? "Review confirmed P7 evidence"
        : confirmedSafeWrite
          ? "Confirmed P7 evidence refresh"
          : "Dry-run audited P7 safe-write refreshes",
      detail: designNext
        ? "Confirmed P7 evidence review is ready. The next plugin action must start with risk model coverage, audit logging, Control Center gates, and targeted MCP tests."
        : reviewConfirmed
        ? "Confirmed evidence refresh is present. Review action-audit and runtime evidence before designing the next plugin action."
        : confirmedSafeWrite
          ? "P7 dry-run and preflight evidence are ready. Run only the selected safe-write refresh with exact confirmation."
          : "P7 gates are ready. Run only dry-run safe-write refreshes before any confirmed evidence refresh.",
      command: safeCommand(engineBrain.p7ActionNextSafeCommand),
      sourcePath: engineBrain.sourcePaths.operatorBrief,
    }
  }

  if (artifactHealth.status !== "ready" && artifactProblem) {
    const guarded = isGuardedLiveCommand(artifactHealth.nextCommand)
    return {
      status: artifactHealth.status === "blocked" ? "blocked" : "warn",
      lane: guarded ? "manual-live-gate" : "artifact-health",
      riskClass: guarded ? "guarded_manual" : "read_only",
      title: guarded ? "Review gated live promotion evidence" : "Refresh stale evidence artifact",
      detail: sanitizeText(artifactHealth.nextAction, 220),
      command: guarded ? "" : safeCommand(artifactHealth.nextCommand),
      sourcePath: artifactProblem.artifactPath,
    }
  }

  if (!apiCostReport || Number(apiCostReport.records_seen || 0) === 0) {
    return {
      status: "warn",
      lane: "api-cost",
      riskClass: "safe_write",
      title: "Refresh API cost evidence",
      detail: !apiCostReport ? "Generate the API cost report before release review." : "API cost report has no records; verify eval artifacts.",
      command: ".\\.venv\\Scripts\\python.exe scripts\\ops\\api_cost_report.py --json-out runtime\\api-cost\\latest.json --md-out runtime\\api-cost\\latest.md",
      sourcePath: toControlCenterDisplayPath(config.costReportPath),
    }
  }

  if (repoStatus !== "PASS") {
    return {
      status: "warn",
      lane: "repo-hygiene",
      riskClass: "safe_write",
      title: "Refresh repo hygiene evidence",
      detail: "Repo hygiene is not PASS; refresh and review findings before sign-off.",
      command: ".\\.venv\\Scripts\\python.exe scripts\\ops\\repo_hygiene_audit.py --json-out runtime\\repo-hygiene\\local-pr-quality.json",
      sourcePath: toControlCenterDisplayPath(config.qualityPath),
    }
  }

  if (otclientHelper.status !== "releasable" && otclientHelper.status !== "promoted" && otclientHelper.nextAction) {
    const guarded = isGuardedLiveCommand(otclientHelper.nextCommand)
    return {
      status: otclientHelper.status === "blocked" ? "blocked" : "warn",
      lane: guarded ? "manual-live-gate" : "helper",
      riskClass: guarded ? "guarded_manual" : "read_only",
      title: guarded ? "Review Helper live gate manually" : "Continue Helper validation gate",
      detail: sanitizeText(otclientHelper.nextAction, 220),
      command: guarded ? "" : safeCommand(otclientHelper.nextCommand),
      sourcePath: otclientHelper.sourcePaths.releaseGate,
    }
  }

  return {
    status: "ready",
    lane: "release-review",
    riskClass: "read_only",
    title: "Review current evidence pack",
    detail: "All operator gates are ready for review. Keep traces fresh before release sign-off.",
    command: "",
    sourcePath: toControlCenterDisplayPath(config.evidenceJsonPath),
  }
}

function isGuardedLiveCommand(command: string): boolean {
  return /PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i.test(command)
}

function jsonHasDuplicateObjectKeys(text: string): boolean {
  let index = 0
  let duplicate = false
  const whitespace = /\s/

  const skipWhitespace = () => {
    while (index < text.length && whitespace.test(text[index])) index += 1
  }
  const parseStringToken = (): string => {
    const start = index
    if (text[index] !== '"') throw new Error("expected JSON string")
    index += 1
    while (index < text.length) {
      const character = text[index]
      if (character === "\\") {
        index += 2
        continue
      }
      index += 1
      if (character === '"') return JSON.parse(text.slice(start, index)) as string
    }
    throw new Error("unterminated JSON string")
  }
  const parseValue = (): void => {
    skipWhitespace()
    const character = text[index]
    if (character === "{") {
      parseObject()
      return
    }
    if (character === "[") {
      index += 1
      skipWhitespace()
      if (text[index] === "]") {
        index += 1
        return
      }
      while (index < text.length) {
        parseValue()
        skipWhitespace()
        if (text[index] === "]") {
          index += 1
          return
        }
        if (text[index] !== ",") throw new Error("invalid JSON array")
        index += 1
      }
      throw new Error("unterminated JSON array")
    }
    if (character === '"') {
      parseStringToken()
      return
    }
    const start = index
    while (index < text.length && !/[\s,}\]]/.test(text[index])) index += 1
    if (start === index) throw new Error("invalid JSON value")
  }
  const parseObject = (): void => {
    index += 1
    const keys = new Set<string>()
    skipWhitespace()
    if (text[index] === "}") {
      index += 1
      return
    }
    while (index < text.length) {
      skipWhitespace()
      const key = parseStringToken()
      if (keys.has(key)) duplicate = true
      keys.add(key)
      skipWhitespace()
      if (text[index] !== ":") throw new Error("invalid JSON object")
      index += 1
      parseValue()
      skipWhitespace()
      if (text[index] === "}") {
        index += 1
        return
      }
      if (text[index] !== ",") throw new Error("invalid JSON object")
      index += 1
    }
    throw new Error("unterminated JSON object")
  }

  try {
    skipWhitespace()
    parseValue()
    skipWhitespace()
    return duplicate || index !== text.length
  } catch {
    return true
  }
}

async function readStrictJsonIfExists(filePath: string): Promise<Record<string, unknown> | null> {
  try {
    const text = await readBoundedTextFileIfExists(filePath, CONTROL_CENTER_EVIDENCE_JSON_MAX_BYTES)
    if (text === null || jsonHasDuplicateObjectKeys(text)) return null
    const parsed = JSON.parse(text)
    return isRecord(parsed) ? parsed : null
  } catch {
    return null
  }
}

async function readJsonIfExists(filePath: string): Promise<Record<string, unknown> | null> {
  try {
    const text = await readBoundedTextFileIfExists(filePath, CONTROL_CENTER_EVIDENCE_JSON_MAX_BYTES)
    if (text === null) {
      return null
    }
    const parsed = JSON.parse(text)
    return isRecord(parsed) ? parsed : null
  } catch {
    return null
  }
}

async function readBoundedTextFileIfExists(filePath: string, maxBytes: number): Promise<string | null> {
  try {
    const pathInfo = await lstat(filePath)
    if (pathInfo.isSymbolicLink() || !pathInfo.isFile()) {
      return null
    }

    const handle = await open(filePath, "r")
    try {
      const fileInfo = await handle.stat()
      if (!fileInfo.isFile()) {
        return null
      }

      const buffer = Buffer.allocUnsafe(maxBytes + 1)
      const { bytesRead } = await handle.read(buffer, 0, maxBytes + 1, 0)
      if (bytesRead > maxBytes) {
        return null
      }
      return buffer.subarray(0, bytesRead).toString("utf-8")
    } finally {
      await handle.close()
    }
  } catch {
    return null
  }
}

async function collectReleaseEvidenceDrilldown(dirPath: string): Promise<ControlCenterEvidence["releaseEvidenceDrilldown"]> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true })
    const sprintDirs = entries.filter((entry) => entry.isDirectory() && entry.name.startsWith("sprint-"))
    const recentFiles: ControlCenterEvidence["releaseEvidenceDrilldown"]["recentFiles"] = []
    const sprintFileCounts = new Map<string, number>()
    let latestModifiedMs = 0
    let latestSprint = ""

    for (const entry of sprintDirs) {
      const sprintDir = path.join(dirPath, entry.name)
      const files = await readdir(sprintDir, { withFileTypes: true })
      let fileCount = 0
      for (const file of files) {
        if (!file.isFile() || !file.name.endsWith(".md")) {
          continue
        }
        fileCount += 1
        const fullPath = path.join(sprintDir, file.name)
        const fileStat = await stat(fullPath)
        if (fileStat.mtimeMs > latestModifiedMs) {
          latestModifiedMs = fileStat.mtimeMs
          latestSprint = entry.name
        }
        recentFiles.push({
          sprint: entry.name,
          path: toControlCenterDisplayPath(fullPath),
          title: await readMarkdownTitle(fullPath),
          modifiedAt: new Date(fileStat.mtimeMs).toISOString(),
          bytes: fileStat.size,
        })
      }
      sprintFileCounts.set(entry.name, fileCount)
    }

    recentFiles.sort((left, right) => Date.parse(right.modifiedAt) - Date.parse(left.modifiedAt) || right.path.localeCompare(left.path))
    const fileCount = Array.from(sprintFileCounts.values()).reduce((total, count) => total + count, 0)
    return {
      status: fileCount > 0 ? "ready" : "missing",
      root: toControlCenterDisplayPath(dirPath),
      fileCount,
      sprintCount: Array.from(sprintFileCounts.values()).filter((count) => count > 0).length,
      latestSprint,
      latestModifiedAt: latestModifiedMs ? new Date(latestModifiedMs).toISOString() : "",
      recentFiles: recentFiles.slice(0, 6),
      nextAction: fileCount > 0 ? "Review latest release evidence before sign-off." : "Generate tracked release evidence before sign-off.",
    }
  } catch {
    return {
      status: "missing",
      root: toControlCenterDisplayPath(dirPath),
      fileCount: 0,
      sprintCount: 0,
      latestSprint: "",
      latestModifiedAt: "",
      recentFiles: [],
      nextAction: "Generate tracked release evidence before sign-off.",
    }
  }
}

async function readMarkdownTitle(filePath: string): Promise<string> {
  try {
    const text = await readBoundedTextFileIfExists(filePath, CONTROL_CENTER_MARKDOWN_TITLE_MAX_BYTES)
    if (text === null) {
      return path.basename(filePath)
    }
    const heading = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => line.startsWith("#"))
    return sanitizeText(heading ? heading.replace(/^#+\s*/, "") : path.basename(filePath), 120)
  } catch {
    return path.basename(filePath)
  }
}

async function collectReleaseComparison(
  config: ControlCenterEvidenceConfig,
  latestReleaseEvidence: ReleaseEvidenceFile | null,
): Promise<ControlCenterEvidence["releaseComparison"]> {
  const runtimeJsonStat = await statIfExists(config.evidenceJsonPath)
  const runtimeMarkdownStat = await statIfExists(config.evidenceMarkdownPath)
  const runtimeEvidence = await readJsonIfExists(config.evidenceJsonPath)
  const currentModifiedMs = Math.max(runtimeJsonStat?.mtimeMs || 0, runtimeMarkdownStat?.mtimeMs || 0)
  const trackedModifiedMs = latestReleaseEvidence ? Date.parse(latestReleaseEvidence.modifiedAt) : 0
  const currentExists = Boolean(runtimeJsonStat && runtimeMarkdownStat)
  const trackedExists = latestReleaseEvidence !== null
  let relation = "missing"
  let status = "missing"
  let nextAction = "Generate runtime evidence pack before release comparison."
  let nextCommand = "python scripts\\ops\\release_evidence_pack.py"

  if (currentExists && !trackedExists) {
    relation = "tracked_missing"
    status = "warn"
    nextAction = "Publish tracked release evidence before sign-off."
    nextCommand = ""
  } else if (!currentExists && trackedExists) {
    relation = "runtime_missing"
  } else if (currentExists && trackedExists) {
    relation =
      Math.abs(currentModifiedMs - trackedModifiedMs) < 1000
        ? "same_timestamp"
        : currentModifiedMs >= trackedModifiedMs
          ? "runtime_newer"
          : "tracked_newer"
    status = relation === "tracked_newer" ? "warn" : "ready"
    nextAction =
      relation === "tracked_newer"
        ? "Refresh runtime evidence pack before sign-off."
        : "Runtime evidence is current against latest tracked release evidence."
    nextCommand = relation === "tracked_newer" ? "python scripts\\ops\\release_evidence_pack.py" : ""
  }

  return {
    status,
    relation,
    currentJsonPath: toControlCenterDisplayPath(config.evidenceJsonPath),
    currentMarkdownPath: toControlCenterDisplayPath(config.evidenceMarkdownPath),
    currentGeneratedAt: String(runtimeEvidence?.generated_at_utc || runtimeEvidence?.generatedAt || ""),
    currentModifiedAt: currentModifiedMs ? new Date(currentModifiedMs).toISOString() : "",
    currentExists,
    trackedPath: latestReleaseEvidence ? toControlCenterDisplayPath(latestReleaseEvidence.path) : "",
    trackedModifiedAt: latestReleaseEvidence?.modifiedAt || "",
    trackedExists,
    minutesBetween:
      currentModifiedMs && trackedModifiedMs
        ? Math.round(Math.abs(currentModifiedMs - trackedModifiedMs) / 60000)
        : null,
    nextAction,
    nextCommand,
  }
}

async function collectActionAuditDrilldown(filePath: string): Promise<ControlCenterEvidence["actionAuditDrilldown"]> {
  try {
    const sample = await readBoundedControlCenterActionAuditLines(filePath)
    const records: Record<string, unknown>[] = []
    let invalidRecordCount = 0

    for (const line of sample.lines) {
      if (line.length > ACTION_AUDIT_MAX_LINE_LENGTH) {
        invalidRecordCount += 1
        continue
      }
      try {
        const parsed = JSON.parse(line)
        if (isRecord(parsed)) {
          records.push(parsed)
        } else {
          invalidRecordCount += 1
        }
      } catch {
        invalidRecordCount += 1
      }
    }

    const recentRecords = records
      .slice(-6)
      .reverse()
      .map((record) => ({
        at: sanitizeText(String(record.at || record.created_at || ""), 80),
        auditId: sanitizeText(String(record.audit_id || ""), 80),
        action: sanitizeText(String(record.action || "unknown"), 80),
        target: sanitizeText(String(record.target || "unknown"), 80),
        riskClass: sanitizeText(String(record.risk_class || "unknown"), 80),
        actorRole: sanitizeText(String(record.actor_role || record.actor || "unknown"), 80),
        authorized: record.authorized === undefined ? "n/a" : record.authorized ? "yes" : "no",
        ok: record.ok === undefined ? "n/a" : record.ok ? "yes" : "no",
        dryRun: record.dry_run === true,
        summary: auditSummary(record),
      }))

    const status =
      records.length > 0
        ? sample.truncated || invalidRecordCount > 0
          ? "warn"
          : "ready"
        : sample.sourceBytes > 0
          ? "warn"
          : "missing"
    const nextAction =
      records.length === 0
        ? "Exercise one read-only Control Center action to create audit evidence."
        : sample.truncated
          ? "Review or rotate the oversized Control Center action audit before sign-off; drilldown is tail-limited."
          : "Review recent action audit records before enabling broader operator actions."
    const nextCommand =
      records.length === 0
        ? "Open Control Center and run one audited read-only action before sign-off."
        : sample.truncated
          ? "Review runtime\\control-center\\action-audit.jsonl retention before sign-off."
          : ""

    return {
      status,
      path: toControlCenterDisplayPath(filePath),
      recordCount: records.length,
      invalidRecordCount,
      truncated: sample.truncated,
      sourceBytes: sample.sourceBytes,
      sampledBytes: sample.sampledBytes,
      latestAt: recentRecords[0]?.at || "",
      actionCounts: countBy(records, "action"),
      riskCounts: countBy(records, "risk_class"),
      authorizedCount: records.filter((record) => record.authorized === true).length,
      deniedCount: records.filter((record) => record.authorized === false).length,
      dryRunCount: records.filter((record) => record.dry_run === true).length,
      failedCount: records.filter((record) => record.ok === false).length,
      recentRecords,
      nextAction,
      nextCommand,
    }
  } catch {
    return {
      status: "missing",
      path: toControlCenterDisplayPath(filePath),
      recordCount: 0,
      invalidRecordCount: 0,
      truncated: false,
      sourceBytes: 0,
      sampledBytes: 0,
      latestAt: "",
      actionCounts: {},
      riskCounts: {},
      authorizedCount: 0,
      deniedCount: 0,
      dryRunCount: 0,
      failedCount: 0,
      recentRecords: [],
      nextAction: "Exercise one read-only Control Center action to create audit evidence.",
      nextCommand: "Open Control Center and run one audited read-only action before sign-off.",
    }
  }
}

export async function readBoundedControlCenterActionAuditLines(filePath: string): Promise<{
  lines: string[]
  truncated: boolean
  sourceBytes: number
  sampledBytes: number
}> {
  const pathInfo = await lstat(filePath)
  if (pathInfo.isSymbolicLink() || !pathInfo.isFile()) {
    throw new Error("Control Center action audit path is not safe to read.")
  }

  const sourceBytes = pathInfo.size
  if (sourceBytes <= 0) {
    return { lines: [], truncated: false, sourceBytes: 0, sampledBytes: 0 }
  }

  const requestedBytes = Math.min(sourceBytes, CONTROL_CENTER_ACTION_AUDIT_MAX_BYTES)
  const start = Math.max(0, sourceBytes - requestedBytes)
  const handle = await open(filePath, "r")

  try {
    const fileStat = await handle.stat()
    if (!fileStat.isFile()) {
      throw new Error("Control Center action audit path is not a file.")
    }

    const buffer = Buffer.alloc(requestedBytes)
    const { bytesRead } = await handle.read(buffer, 0, requestedBytes, start)
    let text = buffer.subarray(0, bytesRead).toString("utf-8")
    const truncated = start > 0
    if (truncated) {
      const firstNewline = text.indexOf("\n")
      text = firstNewline >= 0 ? text.slice(firstNewline + 1) : ""
    }

    return {
      lines: text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean),
      truncated,
      sourceBytes,
      sampledBytes: bytesRead,
    }
  } finally {
    await handle.close()
  }
}

function countBy(records: Record<string, unknown>[], key: string): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const record of records) {
    const value = sanitizeText(String(record[key] || "unknown"), 80)
    counts[value] = (counts[value] || 0) + 1
  }
  return counts
}

function auditSummary(record: Record<string, unknown>): string {
  const reason = sanitizeText(String(record.reason || ""), 120)
  if (reason) return reason
  const status = record.ok === undefined ? "status not reported" : record.ok ? "completed" : "failed"
  const mode = record.dry_run === true ? "dry run" : "executed"
  return `${mode}; ${status}`
}

function sanitizeText(value: string, maxLength: number): string {
  return sanitizeControlCenterDisplayText(value, maxLength)
}

async function collectArtifactHealth(
  config: ControlCenterEvidenceConfig,
  actionAudit: ControlCenterEvidence["actionAuditDrilldown"],
): Promise<ControlCenterEvidence["artifactHealth"]> {
  const manifest = await readJsonIfExists(config.helperManifestPath)
  const readiness = await readJsonIfExists(config.helperReleaseReadinessPath)
  const releaseGate = await readJsonIfExists(config.helperReleaseGatePath)
  const smokePreflight = await readJsonIfExists(config.helperSmokePreflightPath)
  const smokeStatus = await readJsonIfExists(config.helperSmokeStatusPath)
  const livePromotion = await readJsonIfExists(config.helperLivePromotionPath)
  const p7CockpitSmoke = await readJsonIfExists(config.engineBrainP7CockpitSmokePath)
  const p7SafeWriteDryRunSmoke = await readJsonIfExists(config.engineBrainP7SafeWriteDryRunSmokePath)

  const checks: ControlCenterEvidence["artifactHealth"]["checks"] = []
  const manifestAge = await fileAgeMinutes(config.helperManifestPath)
  checks.push({
    name: "helper_manifest_age",
    status: manifestAge === null ? "missing" : manifestAge > FRESH_ARTIFACT_MAX_AGE_MINUTES ? "stale" : "passed",
    detail:
      manifestAge === null
        ? "Helper manifest is missing."
        : manifestAge > FRESH_ARTIFACT_MAX_AGE_MINUTES
          ? "Helper manifest is older than 24 hours; rerun PrepareDev or ValidateDev before sign-off."
          : "Helper manifest was refreshed within 24 hours.",
    artifactPath: toControlCenterDisplayPath(config.helperManifestPath),
    ageMinutes: manifestAge,
  })

  const zipInfo = isRecord(readiness?.zip) ? readiness.zip : {}
  const zipPath = resolveEvidencePath(String(zipInfo.path || ""), config.helperDevDir)
  const expectedZipSha = String(zipInfo.sha256 || "")
  const actualZipSha = zipPath ? await sha256IfExists(zipPath) : ""
  const packageHashStatus =
    !zipPath || !expectedZipSha || !actualZipSha ? "missing" : actualZipSha.toLowerCase() === expectedZipSha.toLowerCase() ? "passed" : "mismatch"
  checks.push({
    name: "helper_package_hash",
    status: packageHashStatus,
    detail:
      packageHashStatus === "passed"
        ? "Versioned Helper ZIP matches release_readiness.json."
        : packageHashStatus === "mismatch"
          ? "Versioned Helper ZIP hash does not match release_readiness.json; rerun PrepareDev or ValidateDev."
          : "Versioned Helper ZIP hash evidence is missing.",
    artifactPath: toControlCenterDisplayPath(zipPath || String(zipInfo.path || "")),
    ageMinutes: zipPath ? await fileAgeMinutes(zipPath) : null,
  })

  const manifestCreatedAt = String(manifest?.created_at || "")
  const preflightManifest = isRecord(smokePreflight?.manifest) ? smokePreflight.manifest : {}
  const preflightManifestCreatedAt = String(preflightManifest.created_at || "")
  const smokeReady =
    smokePreflight?.status === "passed" &&
    (smokeStatus?.status === "ready_for_visual_review" || smokeStatus?.status === "passed")
  const smokePreflightStale = Boolean(manifestCreatedAt && preflightManifestCreatedAt && manifestCreatedAt !== preflightManifestCreatedAt)
  const smokeEvidenceStatus = smokeReady ? "passed" : smokePreflightStale ? "stale" : "missing"
  checks.push({
    name: "helper_smoke_evidence",
    status: smokeEvidenceStatus,
    detail:
      smokeEvidenceStatus === "passed"
        ? "Helper smoke evidence is present for the current staged package."
        : smokeEvidenceStatus === "stale"
          ? "SmokePreflight is stale for the current Helper manifest; rerun SmokePreflight."
          : "Full in-world Helper smoke evidence is missing.",
    artifactPath: toControlCenterDisplayPath(config.helperSmokeStatusPath),
    ageMinutes: await fileAgeMinutes(config.helperSmokeStatusPath),
  })

  const releaseGatePassed = releaseGate?.status === "passed" && releaseGate?.releasable_to_live === true
  const liveApprovalGate = findGate(releaseGate, "live_approval")
  const liveApprovalEvidence = String(liveApprovalGate?.evidence || "")
  if (releaseGatePassed || livePromotion) {
    const livePromotionAge = await fileAgeMinutes(config.helperLivePromotionPath)
    const livePromotionHasApproval = livePromotion?.approval_switch === "ApproveLiveDeploy"
    const durablePromotion = Boolean(
      releaseGatePassed &&
        livePromotionHasApproval &&
        liveApprovalGate?.status === "passed" &&
        liveApprovalEvidence.includes("live_promotion.json"),
    )
    const livePromotionStatus = durablePromotion ? "passed" : livePromotion ? "mismatch" : "missing"
    checks.push({
      name: "helper_live_promotion",
      status: livePromotionStatus,
      detail:
        livePromotionStatus === "passed"
          ? "Live promotion evidence is durable for the current staged package."
          : livePromotionStatus === "mismatch"
            ? "Live promotion evidence exists, but the release gate does not accept it for the current manifest."
            : "Release gate is passed, but durable live promotion evidence is missing.",
      artifactPath: toControlCenterDisplayPath(config.helperLivePromotionPath),
      ageMinutes: livePromotionAge,
    })
  }

  checks.push({
    name: "control_center_action_audit",
    status: actionAudit.recordCount > 0 ? (actionAudit.truncated ? "stale" : "passed") : "missing",
    detail:
      actionAudit.recordCount > 0
        ? actionAudit.truncated
          ? `${actionAudit.recordCount} Control Center action audit records are visible from a bounded tail sample; rotate oversized audit evidence before sign-off.`
          : `${actionAudit.recordCount} Control Center action audit records are present.`
        : "Control Center action audit has no records.",
    artifactPath: toControlCenterDisplayPath(config.actionAuditPath),
    ageMinutes: await fileAgeMinutes(config.actionAuditPath),
  })

  const p7CockpitSmokeStatus = String(p7CockpitSmoke?.status || "missing")
  const p7CockpitSmokeSummary = isRecord(p7CockpitSmoke?.summary) ? p7CockpitSmoke.summary : {}
  const p7CockpitSmokeBlockedCount = Number(p7CockpitSmokeSummary.blocked || 0)
  const p7CockpitSmokeReadyAuditCount = Number(p7CockpitSmokeSummary.ready_safe_write_audit_count || 0)
  const p7CockpitSmokeExpectedAuditCount = Number(p7CockpitSmokeSummary.expected_safe_write_audit_count || 0)
  const p7CockpitSmokeCheckCount = Number(p7CockpitSmokeSummary.checks || 0)
  const p7CockpitSmokePassedCount = Number(p7CockpitSmokeSummary.passed || 0)
  const p7CockpitSmokeHealth =
    p7CockpitSmokeStatus === "ready" && p7CockpitSmokeBlockedCount === 0 ? "passed" : p7CockpitSmoke ? "mismatch" : "missing"
  checks.push({
    name: "p7_cockpit_smoke",
    status: p7CockpitSmokeHealth,
    detail:
      p7CockpitSmokeHealth === "passed"
        ? `P7 cockpit smoke is ready: ${p7CockpitSmokePassedCount}/${p7CockpitSmokeCheckCount} checks and ${p7CockpitSmokeReadyAuditCount}/${p7CockpitSmokeExpectedAuditCount} safe-write audits passed.`
        : p7CockpitSmokeHealth === "mismatch"
          ? "P7 cockpit smoke exists but is not ready; review runtime/control-center/p7-cockpit-smoke.json."
          : "P7 cockpit smoke is missing; run scripts/ops/control_center_p7_cockpit_smoke.py.",
    artifactPath: toControlCenterDisplayPath(config.engineBrainP7CockpitSmokePath),
    ageMinutes: await fileAgeMinutes(config.engineBrainP7CockpitSmokePath),
  })

  const p7DryRunSmokeStatus = String(p7SafeWriteDryRunSmoke?.status || "missing")
  const p7DryRunSmokeSummary = isRecord(p7SafeWriteDryRunSmoke?.summary) ? p7SafeWriteDryRunSmoke.summary : {}
  const p7DryRunSmokeBlockedCount = Number(p7DryRunSmokeSummary.blocked || 0)
  const p7DryRunSmokeCheckCount = Number(p7DryRunSmokeSummary.checks || 0)
  const p7DryRunSmokePassedCount = Number(p7DryRunSmokeSummary.passed || 0)
  const p7DryRunSmokeSafeWriteToolCount = Number(p7DryRunSmokeSummary.safe_write_tool_count || 0)
  const p7DryRunSmokeReadyCount = Number(p7DryRunSmokeSummary.dry_run_ready_count || 0)
  const p7DryRunSmokePreflightReadyCount = Number(p7DryRunSmokeSummary.preflight_ready_count || 0)
  const p7DryRunSmokeBootstrapAllowedCount = Number(p7DryRunSmokeSummary.bootstrap_allowed_count || 0)
  const p7DryRunSmokeHealth =
    p7DryRunSmokeStatus === "ready" &&
    p7DryRunSmokeBlockedCount === 0 &&
    p7DryRunSmokeSafeWriteToolCount > 0 &&
    p7DryRunSmokeReadyCount === p7DryRunSmokeSafeWriteToolCount &&
    p7DryRunSmokePreflightReadyCount === p7DryRunSmokeSafeWriteToolCount &&
    p7DryRunSmokeBootstrapAllowedCount === 0
      ? "passed"
      : p7SafeWriteDryRunSmoke
        ? "mismatch"
        : "missing"
  checks.push({
    name: "p7_safe_write_dry_run_smoke",
    status: p7DryRunSmokeHealth,
    detail:
      p7DryRunSmokeHealth === "passed"
        ? `P7 safe-write dry-run smoke is ready: ${p7DryRunSmokePassedCount}/${p7DryRunSmokeCheckCount} checks, ${p7DryRunSmokeReadyCount}/${p7DryRunSmokeSafeWriteToolCount} dry-run tools passed, ${p7DryRunSmokePreflightReadyCount}/${p7DryRunSmokeSafeWriteToolCount} preflight-ready, ${p7DryRunSmokeBootstrapAllowedCount} bootstrap.`
        : p7DryRunSmokeHealth === "mismatch"
          ? "P7 safe-write dry-run smoke exists but is not ready; review runtime/control-center/p7-safe-write-dry-run-smoke.json."
          : "P7 safe-write dry-run smoke is missing; run scripts/ops/control_center_p7_safe_write_dry_run_smoke.py.",
    artifactPath: toControlCenterDisplayPath(config.engineBrainP7SafeWriteDryRunSmokePath),
    ageMinutes: await fileAgeMinutes(config.engineBrainP7SafeWriteDryRunSmokePath),
  })

  const staleCount = checks.filter((check) => check.status === "stale").length
  const blockedCount = checks.filter((check) => check.status === "missing" || check.status === "mismatch").length
  const status = blockedCount > 0 ? "blocked" : staleCount > 0 ? "warn" : "ready"
  const firstProblem = checks.find((check) => check.status !== "passed")

  return {
    status,
    staleCount,
    blockedCount,
    checks,
    nextAction: firstProblem ? firstProblem.detail : "Evidence artifacts are fresh enough for review.",
    nextCommand:
      firstProblem?.name === "helper_smoke_evidence"
        ? "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokePreflight"
        : firstProblem?.name === "helper_live_promotion"
          ? "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy"
        : firstProblem?.name === "control_center_action_audit"
          ? "Open Control Center and run one audited safe action before sign-off."
        : firstProblem?.name === "p7_cockpit_smoke"
          ? ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_cockpit_smoke.py"
        : firstProblem?.name === "p7_safe_write_dry_run_smoke"
          ? ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_safe_write_dry_run_smoke.py"
          : firstProblem
            ? "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ValidateDev"
            : "",
  }
}

function safeNonnegativeInteger(value: unknown): { value: number; valid: boolean } {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? { value, valid: true }
    : { value: 0, valid: false }
}

function matchesExactRecord(value: unknown, expected: Record<string, unknown>): boolean {
  if (!isRecord(value)) {
    return false
  }
  const expectedEntries = Object.entries(expected)
  return Object.keys(value).length === expectedEntries.length && expectedEntries.every(([key, item]) => value[key] === item)
}

function isBackgroundPinError(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= 96 &&
    (BACKGROUND_PIN_ERROR_VALUES.has(value) ||
      /^live_(?:manifest|promotion)_(?:missing|empty|malformed|oversize|symlink_rejected|not_regular|not_object|changed_during_open|unreadable)$/.test(
        value,
      ) ||
      /^manifest_entry_[0-9]{1,3}_(?:invalid|path_invalid|duplicate|sha256_invalid|bytes_invalid)$/.test(value))
  )
}

function isBackgroundPinRemediation(value: unknown): value is Record<string, unknown> {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "classification",
      "required_action",
      "observer_can_write_trust_anchor",
      "historical_rebinding_allowed",
      "requires_current_release_gate",
      "requires_explicit_live_approval",
    ]) ||
    typeof value.classification !== "string" ||
    !BACKGROUND_PIN_CLASSIFICATION_VALUES.has(value.classification) ||
    typeof value.required_action !== "string" ||
    !BACKGROUND_PIN_REQUIRED_ACTION_VALUES.has(value.required_action) ||
    value.observer_can_write_trust_anchor !== false ||
    value.historical_rebinding_allowed !== false
  ) {
    return false
  }
  const trusted = value.classification === "trusted"
  return (
    value.required_action === (trusted ? "none" : "refresh_official_live_promotion_after_current_gates") &&
    value.requires_current_release_gate === !trusted &&
    value.requires_explicit_live_approval === !trusted
  )
}

function isBackgroundDiagnosticParity(value: unknown): value is Record<string, unknown> {
  const countKeys = [
    "manifest_file_count",
    "matched_file_count",
    "mismatch_count",
    "mutable_drift_count",
    "profile_drift_count",
    "missing_count",
    "invalid_path_count",
    "oversize_count",
    "actual_total_bytes",
  ] as const
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "attempted",
      "status",
      ...countKeys,
      "stable_during_observation",
      "acceptance_allowed",
    ]) ||
    typeof value.attempted !== "boolean" ||
    typeof value.status !== "string" ||
    !BACKGROUND_DIAGNOSTIC_STATUS_VALUES.has(value.status) ||
    !countKeys.every((key) => safeNonnegativeInteger(value[key]).valid) ||
    typeof value.stable_during_observation !== "boolean" ||
    value.acceptance_allowed !== false ||
    value.mutable_drift_count !== value.profile_drift_count
  ) {
    return false
  }
  if (!value.attempted) {
    return value.status === "not_required" || value.status === "unavailable"
  }
  const observedFileCount =
    Number(value.matched_file_count) +
    Number(value.mismatch_count) +
    Number(value.mutable_drift_count) +
    Number(value.missing_count) +
    Number(value.invalid_path_count) +
    Number(value.oversize_count)
  return (value.status === "passed" || value.status === "failed") && observedFileCount <= Number(value.manifest_file_count)
}

function summarizeBackgroundStatus(
  payload: Record<string, unknown> | null,
  artifactPresent: boolean,
  nowMs = Date.now(),
): ControlCenterEvidence["otclientHelper"]["backgroundStatus"] {
  const data = payload ?? {}
  const integrity = isRecord(data.integrity) ? data.integrity : {}
  const capability = isRecord(data.capability) ? data.capability : {}
  const log = isRecord(data.log) ? data.log : {}

  const rawPinErrors = integrity.pin_errors
  const pinErrorsPresent = Object.prototype.hasOwnProperty.call(integrity, "pin_errors")
  const pinErrorsValid =
    Array.isArray(rawPinErrors) &&
    rawPinErrors.length <= 32 &&
    rawPinErrors.every(isBackgroundPinError) &&
    rawPinErrors.length === new Set(rawPinErrors).size
  const pinErrors = pinErrorsValid ? rawPinErrors : []
  const pinRemediation = integrity.pin_remediation
  const pinRemediationPresent = Object.prototype.hasOwnProperty.call(integrity, "pin_remediation")
  const pinRemediationValid = isBackgroundPinRemediation(pinRemediation)
  const diagnosticParity = integrity.diagnostic_parity
  const diagnosticParityPresent = Object.prototype.hasOwnProperty.call(integrity, "diagnostic_parity")
  const diagnosticParityValid = isBackgroundDiagnosticParity(diagnosticParity)

  const rawBlockers = data.blockers
  const blockersValid =
    Array.isArray(rawBlockers) &&
    rawBlockers.length <= 16 &&
    rawBlockers.every((item) => typeof item === "string" && BACKGROUND_BLOCKER_VALUES.has(item))
  const blockers = blockersValid
    ? rawBlockers.map((item) => sanitizeText(item, 160)).filter(Boolean).slice(0, 8)
    : []

  const matchedFileCount = safeNonnegativeInteger(integrity.matched_file_count)
  const manifestFileCount = safeNonnegativeInteger(integrity.manifest_file_count)
  const mutableDriftCount = safeNonnegativeInteger(integrity.mutable_drift_count)
  const profileDriftCount = safeNonnegativeInteger(integrity.profile_drift_count)
  const mismatchCount = safeNonnegativeInteger(integrity.mismatch_count)
  const missingCount = safeNonnegativeInteger(integrity.missing_count)
  const invalidPathCount = safeNonnegativeInteger(integrity.invalid_path_count)
  const oversizeCount = safeNonnegativeInteger(integrity.oversize_count)
  const countFieldsValid = [
    matchedFileCount,
    manifestFileCount,
    mutableDriftCount,
    profileDriftCount,
    mismatchCount,
    missingCount,
    invalidPathCount,
    oversizeCount,
  ].every((item) => item.valid)
  const observedFileCount =
    matchedFileCount.value +
    mismatchCount.value +
    mutableDriftCount.value +
    missingCount.value +
    invalidPathCount.value +
    oversizeCount.value
  const integrityCountConsistent = countFieldsValid && observedFileCount <= manifestFileCount.value
  const integrityDriftConsistent =
    mutableDriftCount.valid && profileDriftCount.valid && mutableDriftCount.value === profileDriftCount.value
  const liveFilesUnchanged = integrity.live_files_unchanged_during_observation
  const statusChecks = isRecord(data.checks) ? data.checks : {}
  const interactionContractValid = matchesExactRecord(data.interaction_contract, BACKGROUND_INTERACTION_CONTRACT)
  const wrapperInvariantsValid = matchesExactRecord(data.wrapper_invariants, BACKGROUND_WRAPPER_INVARIANTS)
  const intrusiveActionsValid = Array.isArray(data.intrusive_actions_performed) && data.intrusive_actions_performed.length === 0
  const generatedAtValue = data.generated_at_utc
  const generatedAt =
    typeof generatedAtValue === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(generatedAtValue)
      ? generatedAtValue
      : ""
  const generatedAtMs = generatedAt ? Date.parse(generatedAt) : Number.NaN
  const ageMs = Number.isFinite(generatedAtMs) ? nowMs - generatedAtMs : null
  const timestampFresh = ageMs !== null && ageMs >= 0 && ageMs <= BACKGROUND_STATUS_MAX_AGE_MS

  const reportedStatusValue = data.status
  const reportedStatus =
    typeof reportedStatusValue === "string" && BACKGROUND_STATUS_VALUES.has(reportedStatusValue)
      ? reportedStatusValue
      : artifactPresent
        ? "invalid"
        : "missing"
  const modeValue = data.mode
  const mode = modeValue === BACKGROUND_STATUS_MODE ? modeValue : artifactPresent ? "invalid" : BACKGROUND_STATUS_MODE
  const processStateValue = data.process_state
  const runtimeStateValue = capability.runtime_state || log.runtime_state
  const integrityStatusValue = integrity.status
  const capabilityStatusValue = capability.status
  let integrityStatusConsistent = false
  if (countFieldsValid && integrityCountConsistent && integrityDriftConsistent) {
    const adverseCounts = [
      mismatchCount.value,
      mutableDriftCount.value,
      missingCount.value,
      invalidPathCount.value,
      oversizeCount.value,
    ]
    if (integrityStatusValue === "passed") {
      integrityStatusConsistent =
        matchedFileCount.value === manifestFileCount.value &&
        adverseCounts.every((count) => count === 0) &&
        liveFilesUnchanged === true
    } else if (integrityStatusValue === "failed") {
      integrityStatusConsistent =
        matchedFileCount.value !== manifestFileCount.value || adverseCounts.some((count) => count > 0)
    } else if (integrityStatusValue === "untrusted_pin") {
      integrityStatusConsistent = matchedFileCount.value === 0 && adverseCounts.every((count) => count === 0)
    }
  }

  const checks: Array<[string, boolean]> = [
    ["schema_version", data.schema_version === BACKGROUND_STATUS_SCHEMA],
    ["mode", modeValue === BACKGROUND_STATUS_MODE],
    ["status", typeof reportedStatusValue === "string" && BACKGROUND_STATUS_VALUES.has(reportedStatusValue)],
    ["advisory_only", data.advisory_only === true],
    ["safe_to_run_while_playing", data.safe_to_run_while_playing === true],
    ["promotion_allowed", data.promotion_allowed === false],
    ["dispatch_allowed", data.dispatch_allowed === false],
    ["runtime_actions", data.runtime_actions === false],
    ["interaction_contract", interactionContractValid],
    ["wrapper_invariants", wrapperInvariantsValid],
    ["checks_no_screen_contract", statusChecks.no_screen_contract === true],
    ["checks_client_process_stable_during_wrapper", statusChecks.client_process_stable_during_wrapper === true],
    ["checks_screenshot_count_stable_during_wrapper", statusChecks.screenshot_count_stable_during_wrapper === true],
    ["intrusive_actions_performed", intrusiveActionsValid],
    ["blockers", blockersValid],
    ["integrity", isRecord(data.integrity)],
    ["capability", isRecord(data.capability)],
    ["process_state", processStateValue === "running" || processStateValue === "not_running" || processStateValue === "ambiguous"],
    ["runtime_state", runtimeStateValue === "armed" || runtimeStateValue === "disarmed" || runtimeStateValue === "unknown"],
    [
      "integrity_status",
      typeof integrityStatusValue === "string" && BACKGROUND_INTEGRITY_STATUS_VALUES.has(integrityStatusValue),
    ],
    [
      "capability_status",
      typeof capabilityStatusValue === "string" && BACKGROUND_CAPABILITY_STATUS_VALUES.has(capabilityStatusValue),
    ],
    ["capability_fresh", typeof capability.fresh === "boolean"],
    ["capability_runtime_actions", capability.runtime_actions === false],
    ["capability_runtime_core_actions", capability.runtime_core_actions === false],
    ["matched_file_count", matchedFileCount.valid],
    ["manifest_file_count", manifestFileCount.valid],
    ["mutable_drift_count", mutableDriftCount.valid],
    ["profile_drift_count", profileDriftCount.valid],
    ["mismatch_count", mismatchCount.valid],
    ["missing_count", missingCount.valid],
    ["invalid_path_count", invalidPathCount.valid],
    ["oversize_count", oversizeCount.valid],
    ["live_files_unchanged_during_observation", typeof liveFilesUnchanged === "boolean"],
    ["integrity_count_consistency", integrityCountConsistent],
    ["integrity_drift_consistency", integrityDriftConsistent],
    ["integrity_status_consistency", integrityStatusConsistent],
    ["pin_errors", !pinErrorsPresent || pinErrorsValid],
    ["pin_remediation", !pinRemediationPresent || pinRemediationValid],
    ["diagnostic_parity", !diagnosticParityPresent || diagnosticParityValid],
    ["generated_at_utc", Number.isFinite(generatedAtMs)],
  ]
  const contractErrors = checks.filter(([, passed]) => !passed).map(([name]) => name)
  const contractValid = payload !== null && contractErrors.length === 0
  const fresh = contractValid && timestampFresh
  const integrityStatus =
    typeof integrityStatusValue === "string" && BACKGROUND_INTEGRITY_STATUS_VALUES.has(integrityStatusValue)
      ? integrityStatusValue
      : "invalid"
  const capabilityStatus =
    typeof capabilityStatusValue === "string" && BACKGROUND_CAPABILITY_STATUS_VALUES.has(capabilityStatusValue)
      ? capabilityStatusValue
      : "invalid"
  const capabilityFresh = capability.fresh === true
  const ready =
    contractValid &&
    fresh &&
    reportedStatus === "ready" &&
    integrityStatus === "passed" &&
    capabilityStatus === "fresh" &&
    capabilityFresh &&
    blockers.length === 0

  const status = !artifactPresent
    ? "missing"
    : !contractValid
      ? "blocked"
      : !fresh
        ? "stale"
        : ready
          ? "ready"
          : reportedStatus === "ready"
            ? "blocked"
            : reportedStatus

  return {
    status,
    reportedStatus,
    mode,
    generatedAt,
    maxAgeSeconds: BACKGROUND_STATUS_MAX_AGE_MS / 1000,
    ageSeconds: ageMs === null ? null : Math.round(ageMs) / 1000,
    fresh,
    contractValid,
    contractErrors,
    advisoryOnly: data.advisory_only === true,
    safeToRunWhilePlaying: data.safe_to_run_while_playing === true,
    promotionAllowed: data.promotion_allowed === true,
    dispatchAllowed: data.dispatch_allowed === true,
    runtimeActions: data.runtime_actions === true,
    processState:
      processStateValue === "running" || processStateValue === "not_running" || processStateValue === "ambiguous"
        ? processStateValue
        : "unknown",
    integrityStatus,
    pinErrors,
    pinClassification: pinRemediationValid ? String(pinRemediation.classification) : "unknown",
    pinRequiredAction: pinRemediationValid ? String(pinRemediation.required_action) : "none",
    pinHistoricalRebindingAllowed: false,
    pinRequiresExplicitLiveApproval: pinRemediationValid && pinRemediation.requires_explicit_live_approval === true,
    diagnosticParityStatus: diagnosticParityValid ? String(diagnosticParity.status) : "unknown",
    diagnosticParityAttempted: diagnosticParityValid && diagnosticParity.attempted === true,
    diagnosticProfileDriftCount: diagnosticParityValid ? Number(diagnosticParity.profile_drift_count) : 0,
    diagnosticStableDuringObservation:
      diagnosticParityValid && diagnosticParity.stable_during_observation === true,
    diagnosticAcceptanceAllowed: false,
    matchedFileCount: matchedFileCount.value,
    manifestFileCount: manifestFileCount.value,
    mutableDriftCount: mutableDriftCount.value,
    capabilityStatus,
    capabilityFresh,
    runtimeState: runtimeStateValue === "armed" || runtimeStateValue === "disarmed" ? runtimeStateValue : "unknown",
    blockers,
  }
}

function hasExactKeys(value: unknown, expected: readonly string[]): value is Record<string, unknown> {
  if (!isRecord(value)) return false
  const keys = Object.keys(value)
  return keys.length === expected.length && expected.every((key) => Object.prototype.hasOwnProperty.call(value, key))
}

function hasConditionsShadowNoActionContract(value: Record<string, unknown>): boolean {
  return (
    CONDITIONS_SHADOW_ACTION_FLAGS.every((key) => value[key] === false) &&
    Array.isArray(value.intrusive_actions_performed) &&
    value.intrusive_actions_performed.length === 0
  )
}

function isConditionsShadowSha(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value) && value !== "0".repeat(64)
}

function conditionsShadowCanonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(conditionsShadowCanonicalValue)
  if (!isRecord(value)) return value
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, conditionsShadowCanonicalValue(value[key])]),
  )
}

function conditionsShadowCanonicalSha(value: unknown): string {
  const encoded = JSON.stringify(conditionsShadowCanonicalValue(value))
  return encoded === undefined ? "" : crypto.createHash("sha256").update(encoded).digest("hex")
}

function isConditionsShadowIdentifier(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9][a-z0-9._-]{0,63}$/.test(value)
}

function isConditionsShadowAge(value: unknown): boolean {
  return value === null || (typeof value === "number" && Number.isSafeInteger(value))
}

function conditionsShadowBlockers(value: unknown): string[] | null {
  if (!Array.isArray(value) || value.length > CONDITIONS_SHADOW_BLOCKER_ORDER.length) return null
  const blockers: string[] = []
  let previousRank = -1
  for (const item of value) {
    if (typeof item !== "string") return null
    const rank = CONDITIONS_SHADOW_BLOCKER_RANK.get(item as (typeof CONDITIONS_SHADOW_BLOCKER_ORDER)[number])
    if (rank === undefined || rank <= previousRank) return null
    blockers.push(item)
    previousRank = rank
  }
  return blockers
}

function stringArraysEqual(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index])
}

function validateConditionsShadowTrace(value: unknown): { valid: boolean; blockers: string[] } {
  if (!hasExactKeys(value, CONDITIONS_SHADOW_TRACE_KEYS)) return { valid: false, blockers: [] }
  const inputHashes = value.input_sha256
  const blockers = conditionsShadowBlockers(value.blockers)
  const status = value.status
  const decision = value.decision
  const fixedContract =
    value.schema_version === CONDITIONS_SHADOW_TRACE_SCHEMA &&
    isConditionsShadowIdentifier(value.trace_id) &&
    value.source === "operational" &&
    typeof value.evaluated_at_unix_ms === "number" &&
    Number.isSafeInteger(value.evaluated_at_unix_ms) &&
    value.evaluated_at_unix_ms > 0 &&
    value.mode === "shadow_only" &&
    value.action === "plan_paralyze_recovery" &&
    value.condition === "paralyze" &&
    value.spell === "exura" &&
    hasExactKeys(inputHashes, CONDITIONS_SHADOW_INPUT_HASH_KEYS) &&
    CONDITIONS_SHADOW_INPUT_HASH_KEYS.every((key) => isConditionsShadowSha(inputHashes[key])) &&
    isConditionsShadowSha(value.canonical_input_sha256) &&
    isConditionsShadowAge(value.observation_age_ms) &&
    isConditionsShadowAge(value.p8_age_ms) &&
    isConditionsShadowAge(value.recovery_trace_age_ms) &&
    isConditionsShadowAge(value.recovery_age_ms) &&
    (status === "shadow_plan_ready" || status === "operational_acceptance_blocked") &&
    (decision === "would_plan_paralyze_recovery" || decision === "hold") &&
    blockers !== null &&
    isConditionsShadowSha(value.decision_sha256) &&
    value.operator_review_required === true &&
    hasConditionsShadowNoActionContract(value)
  if (!fixedContract || blockers === null) return { valid: false, blockers: [] }
  const stateConsistent =
    (status === "shadow_plan_ready" && decision === "would_plan_paralyze_recovery" && blockers.length === 0) ||
    (status === "operational_acceptance_blocked" && decision === "hold" && blockers.length > 0)
  const expectedCanonicalInputSha = conditionsShadowCanonicalSha({
    schema_version: CONDITIONS_SHADOW_INPUT_SCHEMA,
    evaluated_at_unix_ms: value.evaluated_at_unix_ms,
    input_sha256: inputHashes,
  })
  const expectedDecisionSha = conditionsShadowCanonicalSha({
    schema_version: CONDITIONS_SHADOW_TRACE_SCHEMA,
    canonical_input_sha256: value.canonical_input_sha256,
    status,
    decision,
    action: value.action,
    condition: value.condition,
    spell: value.spell,
    observation_age_ms: value.observation_age_ms,
    p8_age_ms: value.p8_age_ms,
    recovery_trace_age_ms: value.recovery_trace_age_ms,
    recovery_age_ms: value.recovery_age_ms,
    blockers,
    operator_review_required: value.operator_review_required,
    ...Object.fromEntries(CONDITIONS_SHADOW_ACTION_FLAGS.map((key) => [key, value[key]])),
    intrusive_actions_performed: value.intrusive_actions_performed,
  })
  const hashesBound =
    value.canonical_input_sha256 === expectedCanonicalInputSha &&
    value.decision_sha256 === expectedDecisionSha &&
    value.trace_id === `conditions-shadow-${expectedDecisionSha.slice(0, 16)}`
  const valid = stateConsistent && hashesBound
  return { valid, blockers: valid ? blockers : [] }
}

function validateConditionsShadowScenarioPack(value: unknown): boolean {
  if (!hasExactKeys(value, CONDITIONS_SHADOW_SCENARIO_PACK_KEYS)) return false
  const total = value.total_count
  const passed = value.passed_count
  const failed = value.failed_count
  const cases = value.cases
  if (
    (value.status !== "passed" && value.status !== "failed") ||
    value.fixture_only !== true ||
    value.operational_readiness_claimed !== false ||
    !isConditionsShadowSha(value.scenario_pack_sha256) ||
    typeof total !== "number" ||
    !Number.isSafeInteger(total) ||
    total < 0 ||
    total > 128 ||
    typeof passed !== "number" ||
    !Number.isSafeInteger(passed) ||
    passed < 0 ||
    typeof failed !== "number" ||
    !Number.isSafeInteger(failed) ||
    failed < 0 ||
    !Array.isArray(cases) ||
    cases.length !== total ||
    !hasConditionsShadowNoActionContract(value)
  ) {
    return false
  }
  let allCasesPassed = true
  const seenNames = new Set<string>()
  for (const item of cases) {
    if (!hasExactKeys(item, CONDITIONS_SHADOW_CASE_KEYS)) return false
    const expectedBlockers = conditionsShadowBlockers(item.expected_blockers)
    const actualBlockers = conditionsShadowBlockers(item.blockers)
    const expectedStatus = item.expected_status
    const actualStatus = item.actual_status
    const name = item.name
    const mutation = item.mutation
    const caseContract =
      isConditionsShadowIdentifier(name) &&
      !seenNames.has(name) &&
      typeof mutation === "string" &&
      CONDITIONS_SHADOW_SCENARIO_MUTATIONS.has(mutation) &&
      (expectedStatus === "shadow_plan_ready" || expectedStatus === "operational_acceptance_blocked") &&
      (actualStatus === "shadow_plan_ready" || actualStatus === "operational_acceptance_blocked") &&
      expectedBlockers !== null &&
      actualBlockers !== null &&
      isConditionsShadowSha(item.canonical_input_sha256) &&
      isConditionsShadowSha(item.decision_sha256) &&
      typeof item.deterministic === "boolean" &&
      typeof item.passed === "boolean" &&
      hasConditionsShadowNoActionContract(item)
    if (!caseContract || expectedBlockers === null || actualBlockers === null) return false
    seenNames.add(name)
    const expectedStatusConsistent =
      (expectedStatus === "shadow_plan_ready" && expectedBlockers.length === 0) ||
      (expectedStatus === "operational_acceptance_blocked" && expectedBlockers.length > 0)
    const actualStatusConsistent =
      (actualStatus === "shadow_plan_ready" && actualBlockers.length === 0) ||
      (actualStatus === "operational_acceptance_blocked" && actualBlockers.length > 0)
    const computedPassed =
      item.deterministic === true &&
      expectedStatusConsistent &&
      actualStatusConsistent &&
      expectedStatus === actualStatus &&
      stringArraysEqual(expectedBlockers, actualBlockers)
    if (item.passed !== computedPassed) return false
    allCasesPassed = allCasesPassed && item.passed === true
  }
  if (total === 0) {
    return value.status === "failed" && passed === 0 && failed === 1 && cases.length === 0
  }
  return (
    passed + failed === total &&
    ((value.status === "passed" && allCasesPassed && passed === total && failed === 0) ||
      (value.status === "failed" && !allCasesPassed && passed < total && failed > 0))
  )
}

function summarizeConditionsShadowReplay(
  payload: Record<string, unknown> | null,
  artifactPresent: boolean,
  nowMs = Date.now(),
): ControlCenterEvidence["otclientHelper"]["conditionsShadowReplay"] {
  const data = payload ?? {}
  const trace = isRecord(data.operational_trace) ? data.operational_trace : {}
  const scenarioPack = isRecord(data.scenario_pack) ? data.scenario_pack : {}
  const traceValidation = validateConditionsShadowTrace(data.operational_trace)
  const scenarioPackValid = validateConditionsShadowScenarioPack(data.scenario_pack)
  const generatedAt = data.generated_at_unix_ms
  const generatedAtValid = typeof generatedAt === "number" && Number.isSafeInteger(generatedAt) && generatedAt > 0
  const reportedStatus =
    data.operational_acceptance_status === "shadow_plan_ready_for_operator_review" ||
    data.operational_acceptance_status === "operational_acceptance_blocked"
      ? data.operational_acceptance_status
      : artifactPresent
        ? "invalid"
        : "missing"
  const scenarioPackStatus = data.scenario_pack_status === "passed" || data.scenario_pack_status === "failed"
    ? data.scenario_pack_status
    : "invalid"
  const checks: Array<[string, boolean]> = [
    ["report_keys", hasExactKeys(data, CONDITIONS_SHADOW_REPORT_KEYS)],
    ["schema_version", data.schema_version === CONDITIONS_SHADOW_REPORT_SCHEMA],
    ["generated_at_unix_ms", generatedAtValid],
    ["mode", data.mode === CONDITIONS_SHADOW_REPORT_MODE],
    ["operational_acceptance_status", reportedStatus !== "invalid" && reportedStatus !== "missing"],
    ["scenario_pack_status", scenarioPackStatus !== "invalid"],
    ["fixture_only_validation_passed", typeof data.fixture_only_validation_passed === "boolean"],
    ["runtime_readiness_claimed", data.runtime_readiness_claimed === false],
    ["no_action_contract", hasConditionsShadowNoActionContract(data)],
    ["operational_trace", traceValidation.valid],
    ["scenario_pack", scenarioPackValid],
    ["generated_trace_binding", generatedAtValid && trace.evaluated_at_unix_ms === generatedAt],
    ["scenario_pack_binding", scenarioPack.status === scenarioPackStatus],
    ["fixture_status_binding", data.fixture_only_validation_passed === (scenarioPackStatus === "passed")],
    [
      "operational_status_binding",
      (reportedStatus === "shadow_plan_ready_for_operator_review" && trace.status === "shadow_plan_ready" && scenarioPackStatus === "passed") ||
        (reportedStatus === "operational_acceptance_blocked" &&
          (trace.status === "operational_acceptance_blocked" || scenarioPackStatus === "failed")),
    ],
  ]
  const contractErrors = artifactPresent ? checks.filter(([, passed]) => !passed).map(([name]) => name) : []
  const contractValid = payload !== null && contractErrors.length === 0
  const ageMs = generatedAtValid ? nowMs - generatedAt : null
  const fresh = contractValid && ageMs !== null && ageMs >= 0 && ageMs <= CONDITIONS_SHADOW_REPORT_MAX_AGE_MS
  const status = !artifactPresent
    ? "missing"
    : !contractValid
      ? "invalid"
      : !fresh
        ? "stale"
        : reportedStatus
  return {
    status,
    reportedStatus,
    generatedAtUnixMs: generatedAtValid ? generatedAt : null,
    maxAgeSeconds: CONDITIONS_SHADOW_REPORT_MAX_AGE_MS / 1000,
    ageSeconds: ageMs === null ? null : Math.round(ageMs) / 1000,
    fresh,
    contractValid,
    contractErrors,
    scenarioPackStatus,
    fixtureOnlyValidationPassed: contractValid && data.fixture_only_validation_passed === true,
    runtimeReadinessClaimed: false,
    traceStatus: typeof trace.status === "string" ? sanitizeText(trace.status, 80) : "missing",
    decision: contractValid && typeof trace.decision === "string" ? sanitizeText(trace.decision, 80) : "hold",
    decisionSha256: isConditionsShadowSha(trace.decision_sha256) ? trace.decision_sha256 : "",
    scenarioTotalCount: safeNonnegativeInteger(scenarioPack.total_count).value,
    scenarioPassedCount: safeNonnegativeInteger(scenarioPack.passed_count).value,
    scenarioFailedCount: safeNonnegativeInteger(scenarioPack.failed_count).value,
    blockers: contractValid ? traceValidation.blockers : [],
    dispatchAllowed: false,
    runtimeActions: false,
    executesPlan: false,
    executeOnceAllowed: false,
    promotionAllowed: false,
  }
}

async function collectOtclientHelperStatus(
  config: ControlCenterEvidenceConfig,
): Promise<ControlCenterEvidence["otclientHelper"]> {
  const manifest = await readJsonIfExists(config.helperManifestPath)
  const validation = await readJsonIfExists(config.helperValidationPath)
  const readiness = await readJsonIfExists(config.helperReleaseReadinessPath)
  const releaseGate = await readJsonIfExists(config.helperReleaseGatePath)
  const goalStatus = await readJsonIfExists(config.helperGoalStatusPath)
  const smokePreflight = await readJsonIfExists(config.helperSmokePreflightPath)
  const smokeStatus = await readJsonIfExists(config.helperSmokeStatusPath)
  const livePromotion = await readJsonIfExists(config.helperLivePromotionPath)
  const backgroundStatus = await readJsonIfExists(config.helperBackgroundStatusPath)
  const backgroundStatusArtifact = await statIfExists(config.helperBackgroundStatusPath)
  const conditionsShadowReplay = await readStrictJsonIfExists(config.helperConditionsShadowReplayPath)
  const conditionsShadowReplayArtifact = await statIfExists(config.helperConditionsShadowReplayPath)

  const releaseGateStatus = String(releaseGate?.status || "missing")
  const validationStatus = String(validation?.status || "missing")
  const readinessStatus = String(readiness?.status || "missing")
  const releaseGateReleasableToLive = releaseGate?.releasable_to_live === true
  const liveApprovalGate = findGate(releaseGate, "live_approval")
  const liveApprovalEvidence = String(liveApprovalGate?.evidence || "")
  const livePromotionHasApproval = livePromotion?.approval_switch === "ApproveLiveDeploy"
  const livePromoted = Boolean(
    releaseGateStatus === "passed" &&
      releaseGateReleasableToLive &&
      liveApprovalGate?.status === "passed" &&
      liveApprovalEvidence.includes("live_promotion.json") &&
      livePromotionHasApproval,
  )
  const livePromotionStatus = livePromoted
    ? "promoted"
    : livePromotion
      ? "present"
      : releaseGateReleasableToLive
        ? "missing"
        : "pending"

  const gates = Array.isArray(releaseGate?.gates) ? releaseGate.gates : []
  const blockers = gates
    .filter((gate) => isRecord(gate) && gate.status !== "passed")
    .map((gate) => {
      if (!isRecord(gate)) return ""
      const name = String(gate.name || "gate")
      const reason = String(gate.reason || gate.status || "pending")
      return `${name}: ${reason}`
    })
    .filter(Boolean)

  const files = Array.isArray(manifest?.files) ? manifest.files : []
  const readinessZip = isRecord(readiness?.zip) ? readiness.zip : {}
  const backgroundSummary = summarizeBackgroundStatus(backgroundStatus, backgroundStatusArtifact !== null)
  const conditionsShadowSummary = summarizeConditionsShadowReplay(
    conditionsShadowReplay,
    conditionsShadowReplayArtifact !== null,
  )
  const releasableToLive = releaseGateReleasableToLive && blockers.length === 0
  let status = "missing"
  if (manifest) {
    status = livePromoted ? "promoted" : releasableToLive ? "releasable" : releaseGateStatus === "blocked" || blockers.length > 0 ? "blocked" : "pending"
  }
  const nextCommand =
    releaseGateStatus === "passed"
      ? String(releaseGate?.next_command || "")
      : String(releaseGate?.next_command || goalStatus?.next_command || smokeStatus?.next_command || "")

  return {
    status,
    helperVersion: String(manifest?.helper_version || readiness?.helper_version || validation?.helper_version || "unknown"),
    manifestHash: await sha256IfExists(config.helperManifestPath),
    validationStatus,
    releaseReadinessStatus: readinessStatus,
    releaseGateStatus,
    releasableToLive,
    smokePreflightStatus: String(smokePreflight?.status || "missing"),
    smokeStatus: String(smokeStatus?.status || "missing"),
    livePromotionStatus,
    livePromoted,
    livePromotionCreatedAt: String(livePromotion?.created_at || ""),
    liveClient: toControlCenterDisplayPath(String(livePromotion?.live_client || "")),
    liveBackupPath: toControlCenterDisplayPath(String(livePromotion?.backup || "")),
    stagedFileCount: files.length,
    packagePath: toControlCenterDisplayPath(String(readinessZip.path || "")),
    packageSha256: String(readinessZip.sha256 || ""),
    blockers: blockers.length ? blockers : Array.isArray(goalStatus?.blockers) ? goalStatus.blockers.map(String) : [],
    backgroundStatus: backgroundSummary,
    conditionsShadowReplay: conditionsShadowSummary,
    nextAction: String(releaseGate?.next_action || goalStatus?.next_action || smokeStatus?.next_action || "Run ValidateDev."),
    nextCommand,
    sourcePaths: {
      devDir: toControlCenterDisplayPath(config.helperDevDir),
      manifest: toControlCenterDisplayPath(config.helperManifestPath),
      validation: toControlCenterDisplayPath(config.helperValidationPath),
      releaseReadiness: toControlCenterDisplayPath(config.helperReleaseReadinessPath),
      releaseGate: toControlCenterDisplayPath(config.helperReleaseGatePath),
      goalStatus: toControlCenterDisplayPath(config.helperGoalStatusPath),
      smokePreflight: toControlCenterDisplayPath(config.helperSmokePreflightPath),
      smokeStatus: toControlCenterDisplayPath(config.helperSmokeStatusPath),
      livePromotion: toControlCenterDisplayPath(config.helperLivePromotionPath),
      backgroundStatus: toControlCenterDisplayPath(config.helperBackgroundStatusPath),
      conditionsShadowReplay: toControlCenterDisplayPath(config.helperConditionsShadowReplayPath),
    },
  }
}

function collectP6PluginHandoff(
  config: ControlCenterEvidenceConfig,
  payload: Record<string, unknown> | null,
  fallbackStatus: string,
  smokePayload: Record<string, unknown> | null,
): ControlCenterEvidence["engineBrain"]["p6PluginHandoff"] {
  const checks = Array.isArray(payload?.checks) ? payload.checks.filter(isRecord) : []
  const checkByName = (name: string) => checks.find((check) => String(check.name || "") === name)
  const marketplaceCheck = checkByName("ctoai_plugin_marketplace_entry")
  const installedCacheCheck = checkByName("ctoai_plugin_installed_cache")
  const mcpContractChecks = checks.filter((check) => String(check.name || "").includes("_mcp_contract"))
  const passedMcpContractCount = mcpContractChecks.filter((check) => String(check.status || "") === "passed").length
  const installedCacheEvidence = sanitizeText(String(installedCacheCheck?.evidence || ""), 160)
  const versionMatch = installedCacheEvidence.match(/version\s+([A-Za-z0-9.+_-]+)/)
  const p6Status = sanitizeText(String(payload?.status || fallbackStatus || "missing"), 80)
  const installedCacheStatus = sanitizeText(String(installedCacheCheck?.status || "missing"), 80)
  const marketplaceStatus = sanitizeText(String(marketplaceCheck?.status || "missing"), 80)
  const smokeSummary = isRecord(smokePayload?.summary) ? smokePayload.summary : {}
  const freshThreadVerification = isRecord(smokePayload?.fresh_thread_verification) ? smokePayload.fresh_thread_verification : {}
  const freshThreadRecommendedToolOrder = Array.isArray(freshThreadVerification.recommended_tool_order)
    ? freshThreadVerification.recommended_tool_order.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 8)
    : []
  const smokeStatus = sanitizeText(String(smokePayload?.status || "missing"), 80)
  const smokeBlockedCount = Number(smokeSummary.blocked || 0)
  const currentThreadToolDiscoveryStatus = sanitizeText(String(smokeSummary.current_thread_tool_discovery_status || "missing"), 120)
  const smokeNextAction = sanitizeText(String(freshThreadVerification.next_action || ""), 260)
  const ready =
    p6Status === "ready_for_plugin_design" &&
    installedCacheStatus === "passed" &&
    marketplaceStatus === "passed" &&
    mcpContractChecks.length > 0 &&
    passedMcpContractCount === mcpContractChecks.length

  return {
    status: !payload ? "missing" : ready ? "ready" : "blocked",
    policy: sanitizeText(String(payload?.policy || ""), 220),
    recommendedNext: sanitizeText(String(payload?.recommended_next || ""), 220),
    checkCount: checks.length,
    passedCheckCount: checks.filter((check) => String(check.status || "") === "passed").length,
    marketplaceStatus,
    installedCacheStatus,
    installedCacheVersion: versionMatch?.[1] || "",
    mcpContractCount: mcpContractChecks.length,
    passedMcpContractCount,
    freshThreadRequired: installedCacheStatus === "passed",
    smokeStatus,
    smokeGeneratedAt: String(smokePayload?.generated_at || ""),
    smokeCheckCount: Number(smokeSummary.checks || 0),
    smokePassedCount: Number(smokeSummary.passed || 0),
    smokeBlockedCount,
    currentThreadToolDiscoveryStatus,
    freshThreadVerificationStatus: sanitizeText(String(freshThreadVerification.status || "missing"), 120),
    freshThreadRecommendedToolOrder,
    smokeNextAction,
    smokeSourcePath: toControlCenterDisplayPath(config.engineBrainP6PluginHandoffSmokePath),
    nextAction: ready
      ? smokeStatus === "ready" && smokeBlockedCount === 0
        ? smokeNextAction ||
          "Open a fresh Codex thread and run ctoai_engine_brain_brief, then ctoai_control_center_cockpit, to verify the installed plugin tool layer."
        : "Run scripts/ops/control_center_p6_plugin_handoff_smoke.py before fresh-thread plugin verification."
      : "Refresh Engine Brain and reinstall the local ctoai-engine-brain plugin before plugin handoff.",
    sourcePath: toControlCenterDisplayPath(config.engineBrainP6ReadinessPath),
  }
}

async function collectEngineBrainStatus(
  config: ControlCenterEvidenceConfig,
): Promise<ControlCenterEvidence["engineBrain"]> {
  const manifest = await readJsonIfExists(config.engineBrainManifestPath)
  const p6Readiness = await readJsonIfExists(config.engineBrainP6ReadinessPath)
  const packManifest = await readJsonIfExists(config.engineBrainPackManifestPath)
  const docSync = await readJsonIfExists(config.engineBrainDocSyncPath)
  const secretGuardrail = await readJsonIfExists(config.engineBrainSecretGuardrailPath)
  const operatorBrief = await readJsonIfExists(config.engineBrainOperatorBriefPath)
  const p6PluginHandoffSmokePayload = await readJsonIfExists(config.engineBrainP6PluginHandoffSmokePath)
  const p7CockpitSmokePayload = await readJsonIfExists(config.engineBrainP7CockpitSmokePath)
  const p7SafeWriteDryRunSmokePayload = await readJsonIfExists(config.engineBrainP7SafeWriteDryRunSmokePath)

  const docSyncStatus = String(manifest?.doc_sync_status || docSync?.status || "missing")
  const secretGuardrailStatus = String(manifest?.secret_guardrail_status || secretGuardrail?.status || "missing")
  const p6ReadinessStatus = String(manifest?.p6_readiness_status || "missing")
  const p6PluginHandoff = collectP6PluginHandoff(config, p6Readiness, p6ReadinessStatus, p6PluginHandoffSmokePayload)
  const manifestP7Status = String(manifest?.p7_operator_brief_status || "")
  const p7OperatorBriefStatus = operatorBrief ? String(operatorBrief.status || "missing") : "missing"
  const p7HardBlockers = Array.isArray(operatorBrief?.hard_blockers) ? operatorBrief.hard_blockers : []
  const p7ActionReadiness = isRecord(operatorBrief?.action_readiness) ? operatorBrief.action_readiness : null
  const p7SafeWriteToolDesign = isRecord(operatorBrief?.safe_write_tool_design) ? operatorBrief.safe_write_tool_design : null
  const p7RoadmapGeneration = isRecord(operatorBrief?.roadmap_generation) ? operatorBrief.roadmap_generation : null
  const p7RoadmapGenerationHardBlockers = Array.isArray(p7RoadmapGeneration?.hard_blockers)
    ? p7RoadmapGeneration.hard_blockers
    : []
  const p7SafeWriteToolSelectedActionId = sanitizeText(String(p7SafeWriteToolDesign?.selected_action_id || ""), 120)
  const enabledSafeWriteTools = Array.isArray(p7ActionReadiness?.enabled_safe_write_tools)
    ? p7ActionReadiness.enabled_safe_write_tools.filter(isRecord)
    : []
  const p7SafeWriteAudits = await Promise.all(
    enabledSafeWriteTools.length
      ? enabledSafeWriteTools.map((tool) =>
          collectLatestAuditRecordForAction(
            config.actionAuditPath,
            sanitizeText(String(tool.action_id || ""), 120),
            sanitizeText(String(tool.mcp_tool || ""), 120),
          ),
        )
      : [collectLatestAuditRecordForAction(config.actionAuditPath, p7SafeWriteToolSelectedActionId, sanitizeText(String(p7SafeWriteToolDesign?.proposed_mcp_tool || ""), 120))],
  )
  const p7SafeWriteAudit =
    p7SafeWriteAudits.find((audit) => audit.expectedAction === p7SafeWriteToolSelectedActionId) ||
    p7SafeWriteAudits[0] ||
    (await collectLatestAuditRecordForAction(config.actionAuditPath, p7SafeWriteToolSelectedActionId, sanitizeText(String(p7SafeWriteToolDesign?.proposed_mcp_tool || ""), 120)))
  const p7ActionCandidateCount = Number(p7ActionReadiness?.candidate_count || 0)
  const p7ActionAuditedCandidateCount = Number(p7ActionReadiness?.audited_candidate_count || 0)
  const p7McpWriteToolCount = Number(p7ActionReadiness?.mcp_write_tool_count || 0)
  const p7EnabledSafeWriteToolCount = enabledSafeWriteTools.length
  const p7SafeWriteAuditCount = p7EnabledSafeWriteToolCount ? p7SafeWriteAudits.length : 0
  const p7ReadySafeWriteAuditCount = p7EnabledSafeWriteToolCount
    ? p7SafeWriteAudits.filter((audit) => audit.status === "ready").length
    : 0
  const p7EnabledSafeWriteToolDetails = enabledSafeWriteTools.map((tool) => {
    const actionId = sanitizeText(String(tool.action_id || ""), 120)
    const matchingAudit = p7SafeWriteAudits.find((audit) => audit.expectedAction === actionId)
    return {
      actionId,
      mcpTool: sanitizeText(String(tool.mcp_tool || ""), 120),
      riskClass: sanitizeText(String(tool.risk_class || ""), 80),
      auditStatus: matchingAudit?.status || "missing",
    }
  })
  const p7OperatorCockpitSummary = p7EnabledSafeWriteToolCount
    ? `${p7EnabledSafeWriteToolCount} enabled safe-write MCP tools; ${p7ReadySafeWriteAuditCount}/${p7SafeWriteAuditCount} audits ready; ${p7McpWriteToolCount} MCP write tools declared.`
    : "No enabled safe-write MCP tools declared in the P7 operator brief."
  const p7Warnings = Array.isArray(operatorBrief?.warnings)
    ? operatorBrief.warnings.map((warning) => sanitizeText(String(warning), 80)).filter(Boolean).slice(0, 6)
    : []
  const p7CockpitSmoke = collectP7CockpitSmokeStatus(config, p7CockpitSmokePayload)
  const p7SafeWriteDryRunSmoke = collectP7SafeWriteDryRunSmokeStatus(config, p7SafeWriteDryRunSmokePayload)
  const requiresP7Brief = Boolean(manifestP7Status)
  const p7BriefReady = !requiresP7Brief || (operatorBrief !== null && p7OperatorBriefStatus === "ready" && p7HardBlockers.length === 0)
  const hasManifest = manifest !== null
  const status = !hasManifest
    ? "missing"
    : docSyncStatus === "passed" && secretGuardrailStatus === "passed" && p7BriefReady
      ? "ready"
      : "blocked"
  const nextAction =
    status === "missing"
      ? "Refresh Engine Brain generated context."
      : !p7BriefReady
        ? "Regenerate the P7 operator brief before expanding operator workflow."
      : status === "blocked"
        ? "Fix Engine Brain doc sync or secret guardrail findings, then refresh."
        : "Use a scoped brain pack for the next implementation lane."
  const nextCommand =
    status === "ready"
      ? ".\\ctoa.ps1 brain pack control-center"
      : ".\\ctoa.ps1 brain refresh"

  return {
    status,
    generatedAt: String(manifest?.generated_at || ""),
    fileCount: Number(manifest?.file_count || 0),
    docSyncStatus,
    secretGuardrailStatus,
    p6ReadinessStatus,
    p6PluginHandoff,
    p7OperatorBriefStatus,
    p7Decision: sanitizeText(String(operatorBrief?.decision || ""), 120),
    p7GeneratedAt: String(operatorBrief?.generated_at || ""),
    p7HardBlockerCount: p7HardBlockers.length,
    p7WarningCount: p7Warnings.length,
    p7Warnings,
    p7NextSafeCommand: sanitizeText(String(operatorBrief?.next_safe_command || ""), 180),
    p7Policy: sanitizeText(String(operatorBrief?.policy || ""), 180),
    p7RoadmapGenerationStatus: sanitizeText(String(p7RoadmapGeneration?.status || "missing"), 80),
    p7RoadmapGenerationDocSyncStatus: sanitizeText(String(p7RoadmapGeneration?.doc_sync_status || "missing"), 80),
    p7RoadmapGenerationDocCount: Number(p7RoadmapGeneration?.doc_count || 0),
    p7RoadmapGenerationReadyDocCount: Number(p7RoadmapGeneration?.ready_doc_count || 0),
    p7RoadmapGenerationHardBlockerCount: p7RoadmapGenerationHardBlockers.length,
    p7RoadmapGenerationNextAction: sanitizeText(String(p7RoadmapGeneration?.next_action || ""), 180),
    p7RoadmapGenerationBlockedUntil: sanitizeText(String(p7RoadmapGeneration?.blocked_until || ""), 180),
    p7ActionReadinessStatus: sanitizeText(String(p7ActionReadiness?.status || "missing"), 80),
    p7ActionReadinessDecision: sanitizeText(String(p7ActionReadiness?.decision || ""), 120),
    p7ActionCandidateCount,
    p7ActionAuditedCandidateCount,
    p7McpWriteToolCount,
    p7EnabledSafeWriteToolCount,
    p7ReadySafeWriteAuditCount,
    p7SafeWriteAuditCount,
    p7OperatorCockpitSummary,
    p7EnabledSafeWriteTools: p7EnabledSafeWriteToolDetails,
    p7ActionNextSafeMode: sanitizeText(String(p7ActionReadiness?.next_safe_mode || ""), 120),
    p7ActionNextSafeCommand: sanitizeText(String(p7ActionReadiness?.next_safe_command || ""), 180),
    p7SafeWriteToolDesignStatus: sanitizeText(String(p7SafeWriteToolDesign?.status || "missing"), 80),
    p7SafeWriteToolDesignDecision: sanitizeText(String(p7SafeWriteToolDesign?.decision || ""), 120),
    p7SafeWriteToolSelectedActionId,
    p7SafeWriteToolProposedMcpTool: sanitizeText(String(p7SafeWriteToolDesign?.proposed_mcp_tool || ""), 120),
    p7SafeWriteToolRiskClass: sanitizeText(String(p7SafeWriteToolDesign?.risk_class || ""), 80),
    p7SafeWriteToolMode: sanitizeText(String(p7SafeWriteToolDesign?.mode || ""), 80),
    p7SafeWriteToolMcpEnabled: Boolean(p7SafeWriteToolDesign?.mcp_enabled),
    p7SafeWriteToolNextSafeCommand: sanitizeText(String(p7SafeWriteToolDesign?.next_safe_command || ""), 180),
    p7SafeWriteAudit,
    p7SafeWriteAudits,
    p7CockpitSmoke,
    p7SafeWriteDryRunSmoke,
    packProfile: String(packManifest?.profile || "missing"),
    packIncludedCount: Number(packManifest?.included_count || 0),
    packTruncatedCount: Number(packManifest?.truncated_count || 0),
    packGeneratedAt: String(packManifest?.generated_at || ""),
    sourcePaths: {
      manifest: toControlCenterDisplayPath(config.engineBrainManifestPath),
      p6Readiness: toControlCenterDisplayPath(config.engineBrainP6ReadinessPath),
      p6PluginHandoffSmoke: toControlCenterDisplayPath(config.engineBrainP6PluginHandoffSmokePath),
      packManifest: toControlCenterDisplayPath(config.engineBrainPackManifestPath),
      ownershipMap: toControlCenterDisplayPath(config.engineBrainOwnershipMapPath),
      docSync: toControlCenterDisplayPath(config.engineBrainDocSyncPath),
      secretGuardrail: toControlCenterDisplayPath(config.engineBrainSecretGuardrailPath),
      operatorBrief: toControlCenterDisplayPath(config.engineBrainOperatorBriefPath),
      p7CockpitSmoke: toControlCenterDisplayPath(config.engineBrainP7CockpitSmokePath),
      p7SafeWriteDryRunSmoke: toControlCenterDisplayPath(config.engineBrainP7SafeWriteDryRunSmokePath),
    },
    nextAction,
    nextCommand,
  }
}

function collectP7CockpitSmokeStatus(
  config: ControlCenterEvidenceConfig,
  payload: Record<string, unknown> | null,
): ControlCenterEvidence["engineBrain"]["p7CockpitSmoke"] {
  const summary = isRecord(payload?.summary) ? payload.summary : {}
  const hardBlockers = Array.isArray(payload?.hard_blockers)
    ? payload.hard_blockers.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 8)
    : []
  const warnings = Array.isArray(payload?.warnings)
    ? payload.warnings.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 8)
    : []
  const status = sanitizeText(String(payload?.status || "missing"), 80)
  const checkCount = Number(summary.checks || 0)
  const passedCount = Number(summary.passed || 0)
  const blockedCount = Number(summary.blocked || 0)
  const readySafeWriteAuditCount = Number(summary.ready_safe_write_audit_count || 0)
  const expectedSafeWriteAuditCount = Number(summary.expected_safe_write_audit_count || 0)
  const nextAction =
    status === "ready" && blockedCount === 0
      ? "P7 cockpit smoke is ready for operator review."
      : status === "missing"
        ? "Run scripts/ops/control_center_p7_cockpit_smoke.py after brain refresh and evidence refresh."
        : hardBlockers.length
          ? `Fix P7 cockpit smoke blocker: ${hardBlockers[0]}.`
          : "Review P7 cockpit smoke warnings before operator handoff."

  return {
    status,
    generatedAt: String(payload?.generated_at || ""),
    checkCount,
    passedCount,
    blockedCount,
    enabledSafeWriteToolCount: Number(summary.enabled_safe_write_tool_count || 0),
    readySafeWriteAuditCount,
    expectedSafeWriteAuditCount,
    actionAuditLineCount: Number(summary.action_audit_line_count || 0),
    hardBlockers,
    warnings,
    nextAction,
    sourcePath: toControlCenterDisplayPath(config.engineBrainP7CockpitSmokePath),
  }
}

function collectP7SafeWriteDryRunSmokeStatus(
  config: ControlCenterEvidenceConfig,
  payload: Record<string, unknown> | null,
): ControlCenterEvidence["engineBrain"]["p7SafeWriteDryRunSmoke"] {
  const summary = isRecord(payload?.summary) ? payload.summary : {}
  const hardBlockers = Array.isArray(payload?.hard_blockers)
    ? payload.hard_blockers.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 8)
    : []
  const warnings = Array.isArray(payload?.warnings)
    ? payload.warnings.map((item) => sanitizeText(String(item), 120)).filter(Boolean).slice(0, 8)
    : []
  const results = Array.isArray(payload?.safe_write_results)
    ? payload.safe_write_results
        .filter(isRecord)
        .map((result) => ({
          actionId: sanitizeText(String(result.action_id || ""), 120),
          mcpTool: sanitizeText(String(result.mcp_tool || ""), 120),
          status: sanitizeText(String(result.status || "missing"), 80),
          auditRecordReady: result.audit_record_ready === true,
          preflightOk: result.preflight_ok === true,
          preflightBootstrapAllowed: result.preflight_bootstrap_allowed === true,
        }))
        .slice(0, 8)
    : []
  const status = sanitizeText(String(payload?.status || "missing"), 80)
  const checkCount = Number(summary.checks || 0)
  const passedCount = Number(summary.passed || 0)
  const blockedCount = Number(summary.blocked || 0)
  const safeWriteToolCount = Number(summary.safe_write_tool_count || 0)
  const dryRunReadyCount = Number(summary.dry_run_ready_count || 0)
  const preflightReadyCount = Number(summary.preflight_ready_count || 0)
  const bootstrapAllowedCount = Number(summary.bootstrap_allowed_count || 0)
  const ready =
    status === "ready" &&
    blockedCount === 0 &&
    safeWriteToolCount > 0 &&
    dryRunReadyCount === safeWriteToolCount &&
    preflightReadyCount === safeWriteToolCount &&
    bootstrapAllowedCount === 0
  const nextAction = ready
    ? "P7 safe-write dry-run smoke is ready for operator review."
    : status === "missing"
      ? "Run scripts/ops/control_center_p7_safe_write_dry_run_smoke.py after P7 cockpit smoke."
      : hardBlockers.length
        ? `Fix P7 safe-write dry-run smoke blocker: ${hardBlockers[0]}.`
        : "Rerun P7 safe-write dry-run smoke until all tools are preflight-ready with zero bootstrap."

  return {
    status,
    generatedAt: String(payload?.generated_at || ""),
    checkCount,
    passedCount,
    blockedCount,
    safeWriteToolCount,
    dryRunReadyCount,
    preflightReadyCount,
    bootstrapAllowedCount,
    hardBlockers,
    warnings,
    results,
    nextAction,
    sourcePath: toControlCenterDisplayPath(config.engineBrainP7SafeWriteDryRunSmokePath),
  }
}

async function collectLatestAuditRecordForAction(
  filePath: string,
  expectedAction: string,
  proposedMcpTool = "",
): Promise<ControlCenterEvidence["engineBrain"]["p7SafeWriteAudit"]> {
  if (!expectedAction) {
    return {
      status: "missing",
      expectedAction: "",
      proposedMcpTool,
      auditId: "",
      latestAt: "",
      riskClass: "",
      actorRole: "",
      authorized: "n/a",
      ok: "n/a",
      dryRun: true,
      summary: "",
      nextAction: "Generate the P7 safe-write design before checking action audit evidence.",
    }
  }

  try {
    const sample = await readBoundedControlCenterActionAuditLines(filePath)
    let latest: Record<string, unknown> | null = null

    for (const line of sample.lines) {
      if (line.length > ACTION_AUDIT_MAX_LINE_LENGTH) {
        continue
      }
      try {
        const parsed = JSON.parse(line)
        if (isRecord(parsed) && String(parsed.action || "") === expectedAction) {
          latest = parsed
        }
      } catch {
        // Invalid audit lines are counted by the main drilldown; this summary only needs the latest matching record.
      }
    }

    if (!latest) {
      return {
        status: sample.truncated ? "warn" : "missing",
        expectedAction,
        proposedMcpTool,
        auditId: "",
        latestAt: "",
        riskClass: "",
        actorRole: "",
        authorized: "n/a",
        ok: "n/a",
        dryRun: true,
        summary: "",
        nextAction: `Run ctoai_evidence_pack_refresh with dry_run=true and verify ${expectedAction} audit evidence before broader actions.`,
      }
    }

    const riskClass = sanitizeText(String(latest.risk_class || "unknown"), 80)
    const authorized = latest.authorized === undefined ? "n/a" : latest.authorized ? "yes" : "no"
    const ok = latest.ok === undefined ? "n/a" : latest.ok ? "yes" : "no"
    const dryRun = latest.dry_run === true
    const status = riskClass === "safe_write" && authorized === "yes" && ok === "yes" ? "ready" : "warn"

    return {
      status,
      expectedAction,
      proposedMcpTool,
      auditId: sanitizeText(String(latest.audit_id || ""), 80),
      latestAt: sanitizeText(String(latest.at || latest.created_at || ""), 80),
      riskClass,
      actorRole: sanitizeText(String(latest.actor_role || latest.actor || "unknown"), 80),
      authorized,
      ok,
      dryRun,
      summary: auditSummary(latest),
      nextAction:
        status !== "ready"
          ? "Review mismatched safe-write audit metadata before enabling more operator actions."
          : dryRun
            ? "Dry-run safe-write evidence is present; confirmed execution remains optional and explicit."
            : "Confirmed safe-write evidence is present; review runtime evidence before adding another write tool.",
    }
  } catch {
    return {
      status: "missing",
      expectedAction,
      proposedMcpTool,
      auditId: "",
      latestAt: "",
      riskClass: "",
      actorRole: "",
      authorized: "n/a",
      ok: "n/a",
      dryRun: true,
      summary: "",
      nextAction: `Run ctoai_evidence_pack_refresh with dry_run=true and verify ${expectedAction} audit evidence before broader actions.`,
    }
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function sanitizeCountMap(value: unknown): Record<string, number> {
  if (!isRecord(value)) {
    return {}
  }
  return Object.fromEntries(
    Object.entries(value)
      .map(([key, count]) => [sanitizeText(String(key), 80), Number(count || 0)] as const)
      .filter(([key, count]) => Boolean(key) && Number.isFinite(count))
      .slice(0, 16),
  )
}

function findGate(report: Record<string, unknown> | null, name: string): Record<string, unknown> | null {
  const gates = Array.isArray(report?.gates) ? report.gates : []
  const gate = gates.find((item) => isRecord(item) && item.name === name)
  return isRecord(gate) ? gate : null
}

async function sha256IfExists(filePath: string): Promise<string> {
  try {
    const pathInfo = await lstat(filePath)
    if (pathInfo.isSymbolicLink() || !pathInfo.isFile()) {
      return ""
    }
    const data = await readFile(filePath)
    return crypto.createHash("sha256").update(data).digest("hex")
  } catch {
    return ""
  }
}

async function fileAgeMinutes(filePath: string): Promise<number | null> {
  try {
    const fileStat = await lstat(filePath)
    if (fileStat.isSymbolicLink() || !fileStat.isFile()) {
      return null
    }
    return Math.max(0, Math.round((Date.now() - fileStat.mtimeMs) / 60000))
  } catch {
    return null
  }
}

async function statIfExists(filePath: string) {
  try {
    const fileStat = await lstat(filePath)
    return fileStat.isSymbolicLink() || !fileStat.isFile() ? null : fileStat
  } catch {
    return null
  }
}

function resolveEvidencePath(value: string, helperDevDir: string): string {
  if (!value) return ""
  const candidate = path.resolve(helperDevDir, value)
  const helperRoot = path.resolve(helperDevDir)
  const relative = path.relative(helperRoot, candidate)
  if (!relative || (!relative.startsWith("..") && !path.isAbsolute(relative))) {
    return candidate
  }
  return ""
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
