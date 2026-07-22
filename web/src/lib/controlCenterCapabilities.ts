import type {
  ControlCenterCapabilityId,
  ControlCenterEvidenceSliceMap,
} from "@/lib/controlCenterEvidence"
import type { PublicEvidenceStatus } from "@/lib/controlCenterEvidenceAdapters"

export const CONTROL_CENTER_SCHEMA_VERSION = "ctoa.control-center.capabilities.v2"

export type ControlCenterCapabilityManifest = {
  schemaVersion: typeof CONTROL_CENTER_SCHEMA_VERSION
  capabilities: Array<{
    id: ControlCenterCapabilityId
    label: string
    minimumRole: "operator"
    refresh: "on-demand"
    readOnly: true
  }>
}

export type OperatorNextDetail = {
  status: PublicEvidenceStatus
  title: string
  detail: string
  lane: "evidence-review"
  riskClass: "read_only"
  readOnly: true
}

export type EngineBrainDetail = {
  status: PublicEvidenceStatus
  p6ReadinessStatus: string
  p6PluginHandoffStatus: PublicEvidenceStatus
  p7: {
    operatorBriefStatus: string
    actionReadinessStatus: string
    safeWriteToolDesignStatus: string
    decision: string
    blockerCount: number
    warningCount: number
    mcpWriteToolCount: number
    enabledSafeWriteToolCount: number
    readySafeWriteAuditCount: number
    safeWriteAuditCount: number
    cockpitSmokeStatus: string
    dryRunSmokeStatus: string
    dryRunReadyCount: number
    preflightReadyCount: number
    safeWriteToolCount: number
    dryRunTools: Array<{
      actionId: string
      mcpTool: string
      riskClass: string
      auditStatus: PublicEvidenceStatus
    }>
  }
  readOnly: true
}

export type ControlCenterCapabilityDetail = {
  schemaVersion: typeof CONTROL_CENTER_SCHEMA_VERSION
  capabilityId: ControlCenterCapabilityId
  collectedAt: string
  status: PublicEvidenceStatus
  readOnly: true
  value:
    | OperatorNextDetail
    | EngineBrainDetail
    | ControlCenterEvidenceSliceMap["repo-hygiene"]["value"]
    | ControlCenterEvidenceSliceMap["release-evidence"]["value"]
    | ControlCenterEvidenceSliceMap["api-cost"]["value"]
    | ControlCenterEvidenceSliceMap["control-center-audit"]["value"]
}

export type ControlCenterCapabilitySummary = {
  schemaVersion: typeof CONTROL_CENTER_SCHEMA_VERSION
  generatedAt: string
  readOnly: true
  capabilities: Array<{
    id: ControlCenterCapabilityId
    status: PublicEvidenceStatus
    label: string
  }>
}

type AnyControlCenterEvidenceSlice = ControlCenterEvidenceSliceMap[ControlCenterCapabilityId]

export const controlCenterCapabilityManifest: ControlCenterCapabilityManifest = {
  schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
  capabilities: [
    { id: "operator-next", label: "Operator next", minimumRole: "operator", refresh: "on-demand", readOnly: true },
    { id: "engine-brain", label: "Engine Brain", minimumRole: "operator", refresh: "on-demand", readOnly: true },
    { id: "repo-hygiene", label: "Repo hygiene", minimumRole: "operator", refresh: "on-demand", readOnly: true },
    { id: "release-evidence", label: "Release evidence", minimumRole: "operator", refresh: "on-demand", readOnly: true },
    { id: "api-cost", label: "API cost", minimumRole: "operator", refresh: "on-demand", readOnly: true },
    { id: "control-center-audit", label: "Control Center audit", minimumRole: "operator", refresh: "on-demand", readOnly: true },
  ],
}

/**
 * Project a private evidence slice into a bounded public capability.  The
 * projector deliberately omits paths, raw payloads, audit identities, actors,
 * reasons, outputs, commands, and any source-specific prompt names.
 */
export function projectControlCenterCapabilityFromSlice(
  slice: AnyControlCenterEvidenceSlice,
): ControlCenterCapabilityDetail {
  if (slice.id === "operator-next") {
    return {
      schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
      capabilityId: slice.id,
      collectedAt: slice.collectedAt,
      status: slice.value.status,
      readOnly: true,
      value: slice.value,
    }
  }

  if (slice.id === "engine-brain") {
    return {
      schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
      capabilityId: slice.id,
      collectedAt: slice.collectedAt,
      status: slice.value.status,
      readOnly: true,
      value: projectEngineBrainCapabilityEvidence(slice.value),
    }
  }

  return {
    schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
    capabilityId: slice.id,
    collectedAt: slice.collectedAt,
    status: slice.value.status,
    readOnly: true,
    value: slice.value,
  }
}

export function projectControlCenterCapability(
  slice: AnyControlCenterEvidenceSlice,
): ControlCenterCapabilityDetail {
  return projectControlCenterCapabilityFromSlice(slice)
}

export function projectOperatorNextCapabilityEvidence(
  engineBrain: ControlCenterEvidenceSliceMap["engine-brain"]["value"],
): OperatorNextDetail {
  if (engineBrain.status === "ready") {
    return {
      status: "ready",
      title: "Review current evidence",
      detail: "The bounded local evidence is ready for an operator review. No action is executed from this capability.",
      lane: "evidence-review",
      riskClass: "read_only",
      readOnly: true,
    }
  }

  const p7Status = engineBrain.p7OperatorBriefStatus || "missing"
  return {
    status: engineBrain.status === "missing" ? "missing" : "blocked",
    title: "Review evidence gate",
    detail: `P6 ${engineBrain.p6ReadinessStatus || "missing"}; P7 ${p7Status}. Review bounded local evidence before any explicitly authorized follow-up.`,
    lane: "evidence-review",
    riskClass: "read_only",
    readOnly: true,
  }
}

export function projectEngineBrainCapabilityEvidence(
  value: ControlCenterEvidenceSliceMap["engine-brain"]["value"],
): EngineBrainDetail {
  return {
    status: value.status,
    p6ReadinessStatus: value.p6ReadinessStatus,
    p6PluginHandoffStatus: value.p6PluginHandoff.status,
    p7: {
      operatorBriefStatus: value.p7OperatorBriefStatus,
      actionReadinessStatus: value.p7ActionReadinessStatus,
      safeWriteToolDesignStatus: value.p7SafeWriteToolDesignStatus,
      decision: value.p7Decision,
      blockerCount: value.p7HardBlockers.length,
      warningCount: value.p7Warnings.length,
      mcpWriteToolCount: value.p7McpWriteToolCount,
      enabledSafeWriteToolCount: value.p7EnabledSafeWriteToolCount,
      readySafeWriteAuditCount: value.p7ReadySafeWriteAuditCount,
      safeWriteAuditCount: value.p7SafeWriteAuditCount,
      cockpitSmokeStatus: value.p7CockpitSmoke.status,
      dryRunSmokeStatus: value.p7SafeWriteDryRunSmoke.status,
      dryRunReadyCount: value.p7SafeWriteDryRunSmoke.dryRunReadyCount,
      preflightReadyCount: value.p7SafeWriteDryRunSmoke.preflightReadyCount,
      safeWriteToolCount: value.p7SafeWriteDryRunSmoke.safeWriteToolCount,
      dryRunTools: value.p7EnabledSafeWriteTools.map((tool) => ({
        actionId: tool.actionId,
        mcpTool: tool.mcpTool,
        riskClass: tool.riskClass,
        auditStatus: tool.auditStatus,
      })),
    },
    readOnly: true,
  }
}

export function projectControlCenterOpsSummary(
  slices: Partial<ControlCenterEvidenceSliceMap>,
): ControlCenterCapabilitySummary {
  const capabilities = controlCenterCapabilityManifest.capabilities
    .filter((capability) => slices[capability.id])
    .map((capability) => ({
      id: capability.id,
      label: capability.label,
      status: slices[capability.id]?.value.status || "missing",
    }))
  return {
    schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    readOnly: true,
    capabilities,
  }
}
