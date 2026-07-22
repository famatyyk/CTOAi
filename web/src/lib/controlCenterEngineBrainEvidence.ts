import { toControlCenterDisplayPath } from "@/lib/controlCenterDisplayPath"
import type { ControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { sanitizeControlCenterDisplayText } from "@/lib/controlCenterRedaction"
import {
  jsonHasDuplicateObjectKeys,
  readBoundedControlCenterActionAuditLines,
  readStrictControlCenterJson,
} from "@/lib/controlCenterEvidenceIo"
import type { PublicEvidenceStatus } from "@/lib/controlCenterEvidenceAdapters"

const MAX_TEXT = 220
const MAX_LIST_ITEMS = 8
const MAX_AUDIT_LINE_CHARS = 16 * 1024

export type EngineBrainCapabilityEvidence = {
  status: PublicEvidenceStatus
  generatedAt: string
  p6ReadinessStatus: string
  p6PluginHandoff: {
    status: PublicEvidenceStatus
    checkCount: number
    passedCheckCount: number
    marketplaceStatus: string
    installedCacheStatus: string
    mcpContractCount: number
    passedMcpContractCount: number
    smokeStatus: string
    smokePassedCount: number
    smokeCheckCount: number
    freshThreadRecommendedToolOrder: string[]
    currentThreadToolDiscoveryStatus: string
  }
  p7OperatorBriefStatus: string
  p7ActionReadinessStatus: string
  p7SafeWriteToolDesignStatus: string
  p7Decision: string
  p7NextSafeCommand: string
  p7HardBlockers: string[]
  p7Warnings: string[]
  p7McpWriteToolCount: number
  p7EnabledSafeWriteToolCount: number
  p7ReadySafeWriteAuditCount: number
  p7SafeWriteAuditCount: number
  p7OperatorCockpitSummary: string
  p7EnabledSafeWriteTools: Array<{
    actionId: string
    mcpTool: string
    riskClass: string
    auditStatus: PublicEvidenceStatus
  }>
  p7SafeWriteAudit: SafeWriteAuditEvidence
  p7SafeWriteAudits: SafeWriteAuditEvidence[]
  p7CockpitSmoke: SmokeEvidence
  p7SafeWriteDryRunSmoke: DryRunSmokeEvidence
  operatorBrief: {
    status: string
    decision: string
    hardBlockerCount: number
  }
  sourcePaths: {
    manifest: string
    p6Readiness: string
    p6PluginHandoffSmoke: string
    operatorBrief: string
    p7CockpitSmoke: string
    p7SafeWriteDryRunSmoke: string
  }
  nextAction: string
  readOnly: true
}

export type SafeWriteAuditEvidence = {
  status: PublicEvidenceStatus
  expectedAction: string
  proposedMcpTool: string
  latestAt: string
  riskClass: string
  actorRole: string
  authorized: "yes" | "no" | "n/a"
  ok: "yes" | "no" | "n/a"
  dryRun: boolean
}

export type SmokeEvidence = {
  status: string
  checkCount: number
  passedCount: number
  blockedCount: number
}

export type DryRunSmokeEvidence = SmokeEvidence & {
  safeWriteToolCount: number
  dryRunReadyCount: number
  preflightReadyCount: number
  bootstrapAllowedCount: number
}

/**
 * Read and summarize the Engine Brain evidence.  It is intentionally a local,
 * bounded, read-only adapter; mutation authority is never derived here.
 */
export async function collectEngineBrainStatus(
  config: ControlCenterEvidenceConfig,
): Promise<EngineBrainCapabilityEvidence> {
  const [
    manifest,
    p6Readiness,
    operatorBrief,
    p6PluginHandoffSmokePayload,
    p7CockpitSmokePayload,
    p7SafeWriteDryRunSmokePayload,
  ] = await Promise.all([
    readStrictControlCenterJson(config.engineBrainManifestPath),
    readStrictControlCenterJson(config.engineBrainP6ReadinessPath),
    readStrictControlCenterJson(config.engineBrainOperatorBriefPath),
    readStrictControlCenterJson(config.engineBrainP6PluginHandoffSmokePath),
    readStrictControlCenterJson(config.engineBrainP7CockpitSmokePath),
    readStrictControlCenterJson(config.engineBrainP7SafeWriteDryRunSmokePath),
  ])

  const p6ReadinessStatus = safeText(manifest?.p6_readiness_status || p6Readiness?.status || "missing", 80)
  const p6PluginHandoff = collectP6PluginHandoff(p6Readiness, p6ReadinessStatus, p6PluginHandoffSmokePayload)
  const p7OperatorBriefStatus = safeText(operatorBrief?.status || "missing", 80)
  const p7ActionReadiness = isRecord(operatorBrief?.action_readiness) ? operatorBrief.action_readiness : {}
  const p7SafeWriteToolDesign = isRecord(operatorBrief?.safe_write_tool_design) ? operatorBrief.safe_write_tool_design : {}
  const p7HardBlockers = boundedTextList(operatorBrief?.hard_blockers, 120)
  const p7Warnings = boundedTextList(operatorBrief?.warnings, 120)
  const enabledSafeWriteTools = Array.isArray(p7ActionReadiness.enabled_safe_write_tools)
    ? p7ActionReadiness.enabled_safe_write_tools.filter(isRecord).slice(0, MAX_LIST_ITEMS)
    : []

  const auditCandidates = enabledSafeWriteTools.length
    ? enabledSafeWriteTools.map((tool) => ({
        actionId: safeText(tool.action_id, 120),
        mcpTool: safeText(tool.mcp_tool, 120),
      }))
    : [
        {
          actionId: safeText(p7SafeWriteToolDesign.selected_action_id, 120),
          mcpTool: safeText(p7SafeWriteToolDesign.proposed_mcp_tool, 120),
        },
      ]
  const p7SafeWriteAudits = await Promise.all(
    auditCandidates.map((candidate) => collectLatestSafeWriteAudit(config.actionAuditPath, candidate.actionId, candidate.mcpTool)),
  )
  const p7SafeWriteAudit =
    p7SafeWriteAudits.find((audit) => audit.expectedAction === safeText(p7SafeWriteToolDesign.selected_action_id, 120)) ||
    p7SafeWriteAudits[0] ||
    emptyAudit("", "")
  const p7ReadySafeWriteAuditCount = p7SafeWriteAudits.filter((audit) => audit.status === "ready").length
  const p7EnabledSafeWriteToolDetails = enabledSafeWriteTools.map((tool) => {
    const actionId = safeText(tool.action_id, 120)
    const audit = p7SafeWriteAudits.find((entry) => entry.expectedAction === actionId)
    return {
      actionId,
      mcpTool: safeText(tool.mcp_tool, 120),
      riskClass: safeText(tool.risk_class, 80),
      auditStatus: audit?.status || "missing",
    }
  })
  const p7McpWriteToolCount = nonnegativeInteger(p7ActionReadiness.mcp_write_tool_count)
  const p7EnabledSafeWriteToolCount = p7EnabledSafeWriteToolDetails.length
  const p7SafeWriteAuditCount = p7EnabledSafeWriteToolCount ? p7SafeWriteAudits.length : 0
  const p7OperatorCockpitSummary = p7EnabledSafeWriteToolCount
    ? `${p7EnabledSafeWriteToolCount} safe-write tools declared; ${p7ReadySafeWriteAuditCount}/${p7SafeWriteAuditCount} dry-run audits ready.`
    : "No safe-write tools are declared in the P7 operator brief."
  const p7CockpitSmoke = collectP7CockpitSmoke(p7CockpitSmokePayload)
  const p7SafeWriteDryRunSmoke = collectP7SafeWriteDryRunSmoke(p7SafeWriteDryRunSmokePayload)
  const docSyncStatus = safeText(manifest?.doc_sync_status || "missing", 80)
  const secretGuardrailStatus = safeText(manifest?.secret_guardrail_status || "missing", 80)
  const p6Ready = p6ReadinessStatus === "ready_for_plugin_design"
  const p7Ready =
    p7OperatorBriefStatus === "ready" &&
    p7HardBlockers.length === 0 &&
    p7CockpitSmoke.status === "ready" &&
    p7SafeWriteDryRunSmoke.status === "ready"
  const status: PublicEvidenceStatus = !manifest
    ? "missing"
    : docSyncStatus === "passed" && secretGuardrailStatus === "passed" && p6Ready && p7Ready
      ? "ready"
      : "blocked"

  return {
    status,
    generatedAt: safeText(manifest?.generated_at || "", 80),
    p6ReadinessStatus,
    p6PluginHandoff,
    p7OperatorBriefStatus,
    p7ActionReadinessStatus: safeText(p7ActionReadiness.status || "missing", 80),
    p7SafeWriteToolDesignStatus: safeText(p7SafeWriteToolDesign.status || "missing", 80),
    p7Decision: safeText(operatorBrief?.decision || "", MAX_TEXT),
    p7NextSafeCommand: safeText(operatorBrief?.next_safe_command || "", MAX_TEXT),
    p7HardBlockers,
    p7Warnings,
    p7McpWriteToolCount,
    p7EnabledSafeWriteToolCount,
    p7ReadySafeWriteAuditCount,
    p7SafeWriteAuditCount,
    p7OperatorCockpitSummary,
    p7EnabledSafeWriteTools: p7EnabledSafeWriteToolDetails,
    p7SafeWriteAudit,
    p7SafeWriteAudits,
    p7CockpitSmoke,
    p7SafeWriteDryRunSmoke,
    operatorBrief: {
      status: p7OperatorBriefStatus,
      decision: safeText(operatorBrief?.decision || "", MAX_TEXT),
      hardBlockerCount: p7HardBlockers.length,
    },
    sourcePaths: {
      manifest: toControlCenterDisplayPath(config.engineBrainManifestPath),
      p6Readiness: toControlCenterDisplayPath(config.engineBrainP6ReadinessPath),
      p6PluginHandoffSmoke: toControlCenterDisplayPath(config.engineBrainP6PluginHandoffSmokePath),
      operatorBrief: toControlCenterDisplayPath(config.engineBrainOperatorBriefPath),
      p7CockpitSmoke: toControlCenterDisplayPath(config.engineBrainP7CockpitSmokePath),
      p7SafeWriteDryRunSmoke: toControlCenterDisplayPath(config.engineBrainP7SafeWriteDryRunSmokePath),
    },
    nextAction:
      status === "ready"
        ? "Review the current bounded Control Center evidence before any explicitly authorized action."
        : "Refresh and review Engine Brain evidence; the Control Center remains read-only and fail-closed.",
    readOnly: true,
  }
}

function collectP6PluginHandoff(
  p6Readiness: Record<string, unknown> | null,
  fallbackStatus: string,
  p6PluginHandoffSmokePayload: Record<string, unknown> | null,
): EngineBrainCapabilityEvidence["p6PluginHandoff"] {
  const checks = Array.isArray(p6Readiness?.checks) ? p6Readiness.checks.filter(isRecord) : []
  const checkByName = (name: string) => checks.find((check) => safeText(check.name, 120) === name)
  const marketplace = checkByName("ctoai_plugin_marketplace_entry")
  const installedCache = checkByName("ctoai_plugin_installed_cache")
  const mcpChecks = checks.filter((check) => safeText(check.name, 120).includes("_mcp_contract"))
  const summary = isRecord(p6PluginHandoffSmokePayload?.summary) ? p6PluginHandoffSmokePayload.summary : {}
  const freshThread = isRecord(p6PluginHandoffSmokePayload?.fresh_thread_verification)
    ? p6PluginHandoffSmokePayload.fresh_thread_verification
    : {}
  const passedMcpContractCount = mcpChecks.filter((check) => safeText(check.status, 80) === "passed").length
  const ready =
    fallbackStatus === "ready_for_plugin_design" &&
    safeText(marketplace?.status, 80) === "passed" &&
    safeText(installedCache?.status, 80) === "passed" &&
    mcpChecks.length > 0 &&
    passedMcpContractCount === mcpChecks.length

  return {
    status: !p6Readiness ? "missing" : ready ? "ready" : "blocked",
    checkCount: checks.length,
    passedCheckCount: checks.filter((check) => safeText(check.status, 80) === "passed").length,
    marketplaceStatus: safeText(marketplace?.status || "missing", 80),
    installedCacheStatus: safeText(installedCache?.status || "missing", 80),
    mcpContractCount: mcpChecks.length,
    passedMcpContractCount,
    smokeStatus: safeText(p6PluginHandoffSmokePayload?.status || "missing", 80),
    smokePassedCount: nonnegativeInteger(summary.passed),
    smokeCheckCount: nonnegativeInteger(summary.checks),
    freshThreadRecommendedToolOrder: boundedTextList(freshThread.recommended_tool_order, 120),
    currentThreadToolDiscoveryStatus: safeText(summary.current_thread_tool_discovery_status || "missing", 120),
  }
}

function collectP7CockpitSmoke(payload: Record<string, unknown> | null): SmokeEvidence {
  const summary = isRecord(payload?.summary) ? payload.summary : {}
  return {
    status: safeText(payload?.status || "missing", 80),
    checkCount: nonnegativeInteger(summary.checks),
    passedCount: nonnegativeInteger(summary.passed),
    blockedCount: nonnegativeInteger(summary.blocked),
  }
}

function collectP7SafeWriteDryRunSmoke(payload: Record<string, unknown> | null): DryRunSmokeEvidence {
  const summary = isRecord(payload?.summary) ? payload.summary : {}
  return {
    ...collectP7CockpitSmoke(payload),
    safeWriteToolCount: nonnegativeInteger(summary.safe_write_tool_count),
    dryRunReadyCount: nonnegativeInteger(summary.dry_run_ready_count),
    preflightReadyCount: nonnegativeInteger(summary.preflight_ready_count),
    bootstrapAllowedCount: nonnegativeInteger(summary.bootstrap_allowed_count),
  }
}

async function collectLatestSafeWriteAudit(
  filePath: string,
  expectedAction: string,
  proposedMcpTool: string,
): Promise<SafeWriteAuditEvidence> {
  if (!expectedAction) return emptyAudit(expectedAction, proposedMcpTool)
  try {
    const sample = await readBoundedControlCenterActionAuditLines(filePath)
    let latest: Record<string, unknown> | null = null
    for (const line of sample.lines) {
      if (line.length > MAX_AUDIT_LINE_CHARS || jsonHasDuplicateObjectKeys(line)) continue
      try {
        const parsed: unknown = JSON.parse(line)
        if (isRecord(parsed) && safeText(parsed.action, 120) === expectedAction) latest = parsed
      } catch {
        // An invalid line is not usable evidence and cannot make the gate pass.
      }
    }
    if (!latest) return emptyAudit(expectedAction, proposedMcpTool)

    const riskClass = safeText(latest.risk_class || "unknown", 80)
    const authorized = latest.authorized === true ? "yes" : latest.authorized === false ? "no" : "n/a"
    const ok = latest.ok === true ? "yes" : latest.ok === false ? "no" : "n/a"
    const dryRun = latest.dry_run === true
    return {
      status: riskClass === "safe_write" && authorized === "yes" && ok === "yes" && dryRun ? "ready" : "warn",
      expectedAction,
      proposedMcpTool,
      latestAt: safeText(latest.at || latest.created_at || "", 80),
      riskClass,
      actorRole: safeText(latest.actor_role || "unknown", 80),
      authorized,
      ok,
      dryRun,
    }
  } catch {
    return emptyAudit(expectedAction, proposedMcpTool)
  }
}

function emptyAudit(expectedAction: string, proposedMcpTool: string): SafeWriteAuditEvidence {
  return {
    status: "missing",
    expectedAction,
    proposedMcpTool,
    latestAt: "",
    riskClass: "",
    actorRole: "unknown",
    authorized: "n/a",
    ok: "n/a",
    dryRun: true,
  }
}

function boundedTextList(value: unknown, maxLength: number): string[] {
  return Array.isArray(value)
    ? value.map((item) => safeText(item, maxLength)).filter(Boolean).slice(0, MAX_LIST_ITEMS)
    : []
}

function safeText(value: unknown, maxLength: number): string {
  return sanitizeControlCenterDisplayText(typeof value === "string" ? value : "", maxLength)
}

function nonnegativeInteger(value: unknown): number {
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}
