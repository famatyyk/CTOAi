import { execFile } from "node:child_process"
import { randomUUID } from "node:crypto"
import { lstatSync, realpathSync, statSync } from "node:fs"
import { appendFile, mkdir } from "node:fs/promises"
import path from "node:path"
import { promisify } from "node:util"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { readStrictControlCenterJson } from "@/lib/controlCenterEvidenceIo"
import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"
import type { ControlCenterRole, ControlCenterRiskClass } from "@/lib/controlCenterPolicy"
import { canRunControlCenterAction, minimumRoleForRiskClass } from "@/lib/controlCenterPolicy"
import { redactControlCenterAuditText as redactAuditText } from "@/lib/controlCenterRedaction"

const execFileAsync = promisify(execFile)

export const CONTROL_CENTER_ACTION_SCHEMA_VERSION = 2
export const P6_CODEX_INTEGRATION_READINESS_PATH = "AI/generated/P6_CODEX_INTEGRATION_READINESS.json"
export const P7_ACTION_READINESS_PATH = "AI/generated/P7_ACTION_READINESS.json"
export const CONTROL_CENTER_DRY_RUN_PROOF_TTL_MS = 15 * 60 * 1000
/** Generated P6/P7 evidence must be as current as the dry-run proof it gates. */
export const CONTROL_CENTER_ACTION_READINESS_TTL_MS = CONTROL_CENTER_DRY_RUN_PROOF_TTL_MS

const SAFE_WRITE_ACTION_IDS = [
  "repo-hygiene-refresh",
  "api-cost-refresh",
  "evidence-pack-refresh",
  "engine-brain-refresh",
  "p7-cockpit-smoke-refresh",
  "roadmap-state-refresh",
  "full-workspace-validation-refresh",
] as const

type SafeWriteActionId = (typeof SAFE_WRITE_ACTION_IDS)[number]
type ActionExecutionMode = "dry_run_first"
type PreflightCheckStatus = "passed" | "blocked" | "required"

/** Mirrors the P7 Engine Brain snapshot contract; it does not authorize tool execution. */
const SAFE_WRITE_MCP_TOOL_BY_ACTION: Record<SafeWriteActionId, string> = {
  "repo-hygiene-refresh": "ctoai_repo_hygiene_refresh",
  "api-cost-refresh": "ctoai_api_cost_refresh",
  "evidence-pack-refresh": "ctoai_evidence_pack_refresh",
  "engine-brain-refresh": "ctoai_engine_brain_refresh",
  "p7-cockpit-smoke-refresh": "ctoai_p7_cockpit_smoke_refresh",
  "roadmap-state-refresh": "ctoai_roadmap_state_refresh",
  "full-workspace-validation-refresh": "ctoai_full_workspace_validation_refresh",
}
const SAFE_WRITE_MCP_TOOLS = Object.values(SAFE_WRITE_MCP_TOOL_BY_ACTION)
const ISO_INSTANT_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/

export type ControlCenterActor = {
  username: string
  displayName: string
  role: ControlCenterRole
}

/**
 * This is deliberately the browser-safe action shape. Command details live only
 * in ActionDefinition below and never cross the capability API boundary.
 */
export type ControlCenterAction = {
  id: SafeWriteActionId
  label: string
  description: string
  target: "local"
  riskClass: ControlCenterRiskClass
  minimumRole: ControlCenterRole
  confirmationText: string
  requiresReason: true
  dryRunAvailable: true
  enabled: true
  executionMode: ActionExecutionMode
  nativeDryRun: boolean
  effect: string
  evidence: string
}

export type ControlCenterPreflightCheck = {
  id: "p7_registration" | "trusted_runtime" | "dry_run_proof"
  status: PreflightCheckStatus
  detail: string
}

export type ControlCenterActionPreflight = {
  schemaVersion: typeof CONTROL_CENTER_ACTION_SCHEMA_VERSION
  status: "ready" | "blocked"
  dryRunAllowed: boolean
  executeAllowed: boolean
  checks: ControlCenterPreflightCheck[]
  blockers: string[]
}

export type ControlCenterActionCapability = ControlCenterAction & {
  preflight: ControlCenterActionPreflight
}

export type ControlCenterActionCapabilityResponse = {
  schemaVersion: typeof CONTROL_CENTER_ACTION_SCHEMA_VERSION
  generatedAt: string
  capabilities: ControlCenterActionCapability[]
}

/** Private server-side result. Route code must project it before returning JSON. */
export type ControlCenterActionResult = {
  action: ControlCenterAction
  dryRun: boolean
  ok: boolean
  output: string
  auditId: string
  completedAt: string
  proofId?: string
  preflight: ControlCenterActionPreflight
}

export type ControlCenterActionResultProjection = {
  schemaVersion: typeof CONTROL_CENTER_ACTION_SCHEMA_VERSION
  actionId: SafeWriteActionId
  dryRun: boolean
  ok: boolean
  status: "dry_run_validated" | "completed" | "failed"
  auditId: string
  completedAt: string
  proofId?: string
  preflight: ControlCenterActionPreflight
  message: string
}

type CommandSpec = {
  file: string
  args: string[]
  cwd?: string
  timeout: number
}

type ActionDefinition = ControlCenterAction & {
  commandSummary: string
  command: (mode: "dry_run" | "execute", reason: string) => CommandSpec
}

type AuditRecord = {
  at: string
  audit_id: string
  actor: string
  actor_role: string
  action: string
  target: string
  risk_class: ControlCenterRiskClass
  minimum_role: ControlCenterRole
  dry_run: boolean
  authorized: boolean
  ok: boolean
  reason: string
  output_preview: string
  preflight_status: "ready" | "blocked"
  preflight_blockers: string[]
  proof_id?: string
  consumed_proof_id?: string
}

type DryRunProof = {
  actionId: SafeWriteActionId
  actorUsername: string
  issuedAt: number
  expiresAt: number
  consumed: boolean
}

type P7Registration = {
  ok: boolean
  blocker: string
}

const dryRunProofs = new Map<string, DryRunProof>()

export class ControlCenterAuthorizationError extends Error {
  statusCode: number

  constructor(message: string, statusCode = 403) {
    super(message)
    this.name = "ControlCenterAuthorizationError"
    this.statusCode = statusCode
  }
}

export class ControlCenterPreflightError extends Error {
  statusCode: number
  preflight: ControlCenterActionPreflight

  constructor(message: string, preflight: ControlCenterActionPreflight, statusCode = 409) {
    super(message)
    this.name = "ControlCenterPreflightError"
    this.statusCode = statusCode
    this.preflight = preflight
  }
}

export function getControlCenterActionSchemaVersion(): typeof CONTROL_CENTER_ACTION_SCHEMA_VERSION {
  return CONTROL_CENTER_ACTION_SCHEMA_VERSION
}

export function redactControlCenterAuditText(value: string, maxLength = 1200): string {
  return redactAuditText(value, maxLength)
}

export function sanitizeControlCenterActionOutput(value: string, maxLength = 4000): string {
  const sanitized = sanitizeControlCenterMarkdownReport(value).trim()
  if (sanitized.length <= maxLength) {
    return sanitized
  }
  return `${sanitized.slice(0, Math.max(0, maxLength - 12)).trimEnd()}\n[truncated]`
}

function getWorkspaceRoot(): string {
  const configured = process.env.CTOA_WORKSPACE_ROOT?.trim()
  if (configured) {
    if (!path.isAbsolute(configured)) {
      throw new Error("CTOA_WORKSPACE_ROOT must be an absolute path for Control Center action execution.")
    }
    const resolved = path.resolve(configured)
    if (!isExistingDirectory(resolved)) {
      throw new Error(`CTOA_WORKSPACE_ROOT is not an existing directory: ${configured}`)
    }
    return realpathSync(resolved)
  }
  const cwd = process.cwd()
  const root = path.basename(cwd) === "web" ? path.dirname(cwd) : cwd
  return realpathSync(root)
}

function isExistingFile(filePath: string): boolean {
  try {
    return statSync(filePath).isFile()
  } catch {
    return false
  }
}

function isExistingDirectory(filePath: string): boolean {
  try {
    return statSync(filePath).isDirectory()
  } catch {
    return false
  }
}

export function resolveControlCenterWorkspaceRoot(): string {
  return getWorkspaceRoot()
}

export function resolveControlCenterWorkspaceFile(root: string, relativePath: string): string {
  if (path.isAbsolute(relativePath)) {
    throw new Error("Control Center action scripts must be repo-relative paths.")
  }

  const resolvedRoot = realpathSync(path.resolve(root))
  const resolvedPath = path.resolve(resolvedRoot, relativePath)
  const relative = path.relative(resolvedRoot, resolvedPath)
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Control Center action script escapes the workspace root: ${relativePath}`)
  }
  if (!isExistingFile(resolvedPath)) {
    throw new Error(`Control Center action script not found: ${relativePath}`)
  }
  if (lstatSync(resolvedPath).isSymbolicLink()) {
    throw new Error(`Control Center action script must not be a symlink: ${relativePath}`)
  }

  const realPath = realpathSync(resolvedPath)
  const realRelative = path.relative(resolvedRoot, realPath)
  if (realRelative.startsWith("..") || path.isAbsolute(realRelative)) {
    throw new Error(`Control Center action script resolves outside the workspace root: ${relativePath}`)
  }
  return realPath
}

export function resolveControlCenterPython(root: string): string {
  const configured = process.env.CTOA_PYTHON_BIN?.trim()
  if (configured) {
    if (!path.isAbsolute(configured)) {
      throw new Error("CTOA_PYTHON_BIN must be an absolute path for Control Center action execution.")
    }
    if (!isExistingFile(configured)) {
      throw new Error(`CTOA_PYTHON_BIN is not an existing file: ${configured}`)
    }
    return configured
  }

  const localPython =
    process.platform === "win32"
      ? path.join(root, ".venv", "Scripts", "python.exe")
      : path.join(root, ".venv", "bin", "python")

  if (isExistingFile(localPython)) {
    return localPython
  }

  throw new Error(
    `Trusted Python executable not found for Control Center action execution. Set CTOA_PYTHON_BIN to an absolute Python path or create ${localPython}.`,
  )
}

function pythonCommand(scriptRelativePath: string, args: string[], timeout = 120000): CommandSpec {
  const root = resolveControlCenterWorkspaceRoot()
  const python = resolveControlCenterPython(root)
  const scriptPath = resolveControlCenterWorkspaceFile(root, scriptRelativePath)
  return {
    file: python,
    args: [scriptPath, ...args],
    cwd: root,
    timeout,
  }
}

function actionCatalog(): ActionDefinition[] {
  return [
    {
      id: "repo-hygiene-refresh",
      label: "Refresh repo hygiene snapshot",
      description: "Rebuild the bounded local repository hygiene evidence.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh repo hygiene snapshot",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: false,
      effect: "Refreshes a local repository-quality summary.",
      evidence: "Writes a redacted action-audit result.",
      commandSummary: "python scripts/ops/repo_hygiene_audit.py --json-out runtime/repo-hygiene/local-pr-quality.json",
      command: () =>
        pythonCommand("scripts/ops/repo_hygiene_audit.py", ["--json-out", "runtime/repo-hygiene/local-pr-quality.json"], 120000),
    },
    {
      id: "api-cost-refresh",
      label: "Refresh API cost report",
      description: "Rebuild the bounded local API-cost evidence summary.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh api cost report",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: false,
      effect: "Refreshes a local cost-evidence summary.",
      evidence: "Writes a redacted action-audit result.",
      commandSummary: "python scripts/ops/api_cost_report.py --json-out runtime/api-cost/latest.json --md-out runtime/api-cost/latest.md",
      command: () =>
        pythonCommand(
          "scripts/ops/api_cost_report.py",
          ["--json-out", "runtime/api-cost/latest.json", "--md-out", "runtime/api-cost/latest.md"],
          180000,
        ),
    },
    {
      id: "evidence-pack-refresh",
      label: "Rebuild evidence pack",
      description: "Rebuild the compact local evidence pack used for sign-off.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh evidence pack",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: false,
      effect: "Refreshes the bounded sign-off evidence pack.",
      evidence: "Writes a redacted action-audit result.",
      commandSummary: "python scripts/ops/release_evidence_pack.py --json-out runtime/evidence/latest.json --md-out runtime/evidence/latest.md",
      command: () =>
        pythonCommand(
          "scripts/ops/release_evidence_pack.py",
          ["--json-out", "runtime/evidence/latest.json", "--md-out", "runtime/evidence/latest.md"],
          180000,
        ),
    },
    {
      id: "engine-brain-refresh",
      label: "Refresh Engine Brain context",
      description: "Regenerate bounded Engine Brain context from the local workspace.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh engine brain context",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: false,
      effect: "Refreshes generated local context.",
      evidence: "Writes a redacted action-audit result.",
      commandSummary: "python scripts/ops/engine_brain_index.py",
      command: () => pythonCommand("scripts/ops/engine_brain_index.py", [], 180000),
    },
    {
      id: "p7-cockpit-smoke-refresh",
      label: "Refresh P7 cockpit smoke",
      description: "Regenerate bounded P7 cockpit-smoke evidence from local sources.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh p7 cockpit smoke",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: false,
      effect: "Refreshes local P7 smoke evidence.",
      evidence: "Writes a redacted action-audit result.",
      commandSummary: "python scripts/ops/control_center_p7_cockpit_smoke.py",
      command: () => pythonCommand("scripts/ops/control_center_p7_cockpit_smoke.py", [], 180000),
    },
    {
      id: "roadmap-state-refresh",
      label: "Refresh adaptive roadmap state",
      description: "Run the fixed P13 roadmap-state generator with its native dry-run gate.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh roadmap state",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: true,
      effect: "Refreshes only the bounded adaptive roadmap state outputs.",
      evidence: "Uses native dry-run, preflight, and hash-bound audit evidence.",
      commandSummary: "python scripts/ops/ctoai_roadmap_state.py --dry-run true|false",
      command: (mode, reason) =>
        pythonCommand(
          "scripts/ops/ctoai_roadmap_state.py",
          [
            "--dry-run",
            mode === "dry_run" ? "true" : "false",
            ...(mode === "execute" ? ["--confirmation", "refresh roadmap state"] : []),
            "--reason",
            reason || "Control Center bounded roadmap refresh",
          ],
          180000,
        ),
    },
    {
      id: "full-workspace-validation-refresh",
      label: "Refresh full workspace validation",
      description: "Run the fixed workspace validation registry through its native dry-run gate.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      confirmationText: "refresh full workspace validation",
      requiresReason: true,
      dryRunAvailable: true,
      enabled: true,
      executionMode: "dry_run_first",
      nativeDryRun: true,
      effect: "Refreshes only the bounded full-workspace validation evidence.",
      evidence: "Uses native dry-run, fixed registry inputs, and a redacted action audit.",
      commandSummary: "python scripts/ops/ctoa_full_workspace_validation.py --dry-run true|false",
      command: (mode, reason) =>
        pythonCommand(
          "scripts/ops/ctoa_full_workspace_validation.py",
          [
            "--dry-run",
            mode === "dry_run" ? "true" : "false",
            ...(mode === "execute" ? ["--confirmation", "refresh full workspace validation"] : []),
            "--reason",
            reason || "Control Center bounded full workspace validation refresh",
          ],
          1200000,
        ),
    },
  ]
}

function toPublicAction(definition: ActionDefinition): ControlCenterAction {
  const { command, commandSummary, ...action } = definition
  void command
  void commandSummary
  return action
}

export function listControlCenterActions(): ControlCenterAction[] {
  return actionCatalog().map(toPublicAction)
}

export function getControlCenterAction(actionId: string): ControlCenterAction | null {
  return listControlCenterActions().find((item) => item.id === actionId) || null
}

function findActionDefinition(actionId: string): ActionDefinition | null {
  return actionCatalog().find((item) => item.id === actionId) || null
}

function auditId(completedAt: string, actionId: string): string {
  return `${completedAt.replace(/[^0-9]/g, "")}-${actionId}-${randomUUID()}`
}

function publicPreflight(
  registration: P7Registration,
  trustedRuntime: boolean,
  proof: ReturnType<typeof recentSuccessfulDryRun>,
): ControlCenterActionPreflight {
  const checks: ControlCenterPreflightCheck[] = [
    {
      id: "p7_registration",
      status: registration.ok ? "passed" : "blocked",
      detail: registration.ok ? "P7 safe-write registration is current." : "P7 safe-write registration is not ready.",
    },
    {
      id: "trusted_runtime",
      status: trustedRuntime ? "passed" : "blocked",
      detail: trustedRuntime ? "Trusted local runtime is available." : "Trusted local runtime is unavailable.",
    },
    {
      id: "dry_run_proof",
      status: proof.status,
      detail:
        proof.status === "passed"
          ? "A current dry-run proof is available for this execution gate."
          : proof.status === "required"
            ? "Validate a dry-run before opening the execution gate."
            : "The dry-run proof is not valid for this execution gate.",
    },
  ]
  const blockers = [
    ...(registration.ok ? [] : [registration.blocker]),
    ...(trustedRuntime ? [] : ["trusted_runtime_unavailable"]),
    ...(proof.status === "blocked" ? [proof.blocker] : []),
  ]
  const dryRunAllowed = registration.ok && trustedRuntime
  return {
    schemaVersion: CONTROL_CENTER_ACTION_SCHEMA_VERSION,
    status: dryRunAllowed ? "ready" : "blocked",
    dryRunAllowed,
    executeAllowed: dryRunAllowed && proof.status === "passed",
    checks,
    blockers,
  }
}

async function readWorkspaceReadinessArtifact(relativePath: string): Promise<Record<string, unknown> | null> {
  try {
    const root = resolveControlCenterWorkspaceRoot()
    const readinessPath = resolveControlCenterWorkspaceFile(root, relativePath)
    return await readStrictControlCenterJson(readinessPath)
  } catch {
    return null
  }
}

async function readP6ActionReadiness(): Promise<Record<string, unknown> | null> {
  return readWorkspaceReadinessArtifact(P6_CODEX_INTEGRATION_READINESS_PATH)
}

async function readP7ActionReadiness(): Promise<Record<string, unknown> | null> {
  return readWorkspaceReadinessArtifact(P7_ACTION_READINESS_PATH)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

type ReadinessTimestamp =
  | { ok: true; timestamp: number }
  | { ok: false; blocker: string }

function currentReadinessTimestamp(value: unknown, blockerPrefix: string, now: number): ReadinessTimestamp {
  if (typeof value !== "string" || !ISO_INSTANT_PATTERN.test(value)) {
    return { ok: false, blocker: `${blockerPrefix}_generated_at_invalid` }
  }
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) {
    return { ok: false, blocker: `${blockerPrefix}_generated_at_invalid` }
  }
  const age = now - timestamp
  if (age < 0 || age > CONTROL_CENTER_ACTION_READINESS_TTL_MS) {
    return { ok: false, blocker: `${blockerPrefix}_stale` }
  }
  return { ok: true, timestamp }
}

function p6ReadinessBinding(payload: Record<string, unknown> | null, now: number): ReadinessTimestamp {
  if (!payload) return { ok: false, blocker: "p6_action_readiness_missing" }
  if (payload.schema_version !== 1) return { ok: false, blocker: "p6_action_readiness_schema_invalid" }
  if (payload.status !== "ready_for_plugin_design") {
    return { ok: false, blocker: "p6_action_readiness_not_ready" }
  }
  const checks = Array.isArray(payload.checks) ? payload.checks : []
  if (!checks.length || checks.some((check) => !isRecord(check) || check.status !== "passed")) {
    return { ok: false, blocker: "p6_action_readiness_checks_incomplete" }
  }
  return currentReadinessTimestamp(payload.generated_at, "p6_action_readiness", now)
}

function hasExactExpectedMcpTools(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.length === SAFE_WRITE_MCP_TOOLS.length &&
    value.every((item) => typeof item === "string" && SAFE_WRITE_MCP_TOOLS.includes(item)) &&
    new Set(value).size === SAFE_WRITE_MCP_TOOLS.length
  )
}

function p7RegistrationForAction(
  p6Payload: Record<string, unknown> | null,
  p7Payload: Record<string, unknown> | null,
  actionId: SafeWriteActionId,
  now: number,
): P7Registration {
  const p6Timestamp = p6ReadinessBinding(p6Payload, now)
  if (!p6Timestamp.ok) return p6Timestamp

  if (!p7Payload) return { ok: false, blocker: "p7_action_readiness_missing" }
  if (p7Payload.schema_version !== 1) return { ok: false, blocker: "p7_action_readiness_schema_invalid" }
  if (p7Payload.status !== "safe_write_tools_enabled") {
    return { ok: false, blocker: "p7_action_readiness_not_ready" }
  }
  const p7Timestamp = currentReadinessTimestamp(p7Payload.generated_at, "p7_action_readiness", now)
  if (!p7Timestamp.ok) return p7Timestamp
  if (p7Timestamp.timestamp !== p6Timestamp.timestamp) {
    return { ok: false, blocker: "p6_p7_readiness_snapshot_mismatch" }
  }
  if (
    p7Payload.candidate_count !== SAFE_WRITE_ACTION_IDS.length ||
    p7Payload.mcp_write_tool_count !== SAFE_WRITE_ACTION_IDS.length ||
    !hasExactExpectedMcpTools(p7Payload.mcp_write_tools)
  ) {
    return { ok: false, blocker: "p7_action_registration_incomplete" }
  }

  const candidates = Array.isArray(p7Payload.safe_write_candidates) ? p7Payload.safe_write_candidates : []
  const enabled = Array.isArray(p7Payload.enabled_safe_write_tools) ? p7Payload.enabled_safe_write_tools : []
  if (candidates.length !== SAFE_WRITE_ACTION_IDS.length || enabled.length !== SAFE_WRITE_ACTION_IDS.length) {
    return { ok: false, blocker: "p7_action_registration_incomplete" }
  }

  const candidateById = new Map<string, Record<string, unknown>>()
  for (const candidate of candidates) {
    if (!isRecord(candidate) || typeof candidate.id !== "string" || candidateById.has(candidate.id)) {
      return { ok: false, blocker: "p7_action_registration_incomplete" }
    }
    candidateById.set(candidate.id, candidate)
  }
  const enabledByAction = new Map<string, Record<string, unknown>>()
  for (const item of enabled) {
    if (!isRecord(item) || typeof item.action_id !== "string" || enabledByAction.has(item.action_id)) {
      return { ok: false, blocker: "p7_action_registration_incomplete" }
    }
    enabledByAction.set(item.action_id, item)
  }

  for (const expectedActionId of SAFE_WRITE_ACTION_IDS) {
    const candidate = candidateById.get(expectedActionId)
    const enabledTool = enabledByAction.get(expectedActionId)
    const expectedMcpTool = SAFE_WRITE_MCP_TOOL_BY_ACTION[expectedActionId]
    if (
      !candidate ||
      !enabledTool ||
      candidate.risk_class !== "safe_write" ||
      candidate.control_center_enabled !== true ||
      candidate.risk_model_present !== true ||
      candidate.plugin_mcp_allowed !== true ||
      candidate.audit_ready !== true ||
      !Array.isArray(candidate.missing_gates) ||
      candidate.missing_gates.length !== 0 ||
      candidate.expected_mcp_tool !== expectedMcpTool ||
      enabledTool.risk_class !== "safe_write" ||
      enabledTool.mcp_tool !== expectedMcpTool
    ) {
      return { ok: false, blocker: "p7_action_audit_binding_incomplete" }
    }
  }

  return candidateById.has(actionId) && enabledByAction.has(actionId)
    ? { ok: true, blocker: "" }
    : { ok: false, blocker: "p7_action_registration_incomplete" }
}

function trustedRuntimeAvailable(definition: ActionDefinition): boolean {
  try {
    definition.command("dry_run", "")
    return true
  } catch {
    return false
  }
}

export function recentSuccessfulDryRun(input: {
  actionId: SafeWriteActionId
  actor?: ControlCenterActor | null
  proofId?: string
  now?: number
}): { status: PreflightCheckStatus; blocker: string } {
  if (!input.proofId) return { status: "required", blocker: "" }
  const proof = dryRunProofs.get(input.proofId)
  const now = input.now ?? Date.now()
  if (!proof || proof.actionId !== input.actionId) return { status: "blocked", blocker: "dry_run_proof_invalid" }
  if (!input.actor || proof.actorUsername !== input.actor.username) {
    return { status: "blocked", blocker: "dry_run_proof_actor_mismatch" }
  }
  if (proof.consumed) return { status: "blocked", blocker: "dry_run_proof_consumed" }
  if (proof.expiresAt <= now) {
    dryRunProofs.delete(input.proofId)
    return { status: "blocked", blocker: "dry_run_proof_expired" }
  }
  return { status: "passed", blocker: "" }
}

export async function evaluateActionPreflight(
  action: string | Pick<ControlCenterAction, "id">,
  input: { actor?: ControlCenterActor | null; proofId?: string; now?: number } = {},
): Promise<ControlCenterActionPreflight> {
  const actionId = typeof action === "string" ? action : action.id
  const definition = findActionDefinition(actionId)
  if (!definition) {
    return {
      schemaVersion: CONTROL_CENTER_ACTION_SCHEMA_VERSION,
      status: "blocked",
      dryRunAllowed: false,
      executeAllowed: false,
      checks: [
        { id: "p7_registration", status: "blocked", detail: "P7 safe-write registration is not ready." },
        { id: "trusted_runtime", status: "blocked", detail: "Trusted local runtime is unavailable." },
        { id: "dry_run_proof", status: "required", detail: "Validate a dry-run before opening the execution gate." },
      ],
      blockers: ["unknown_action"],
    }
  }
  const now = input.now ?? Date.now()
  const [p6Readiness, p7Readiness] = await Promise.all([readP6ActionReadiness(), readP7ActionReadiness()])
  const registration = p7RegistrationForAction(p6Readiness, p7Readiness, definition.id, now)
  const proof = recentSuccessfulDryRun({ actionId: definition.id, actor: input.actor, proofId: input.proofId, now })
  return publicPreflight(registration, trustedRuntimeAvailable(definition), proof)
}

export async function listControlCenterActionCapabilities(input: {
  actor?: ControlCenterActor | null
} = {}): Promise<ControlCenterActionCapabilityResponse> {
  const actor = input.actor || null
  const capabilities = actor
    ? await Promise.all(
        actionCatalog()
          .filter((definition) => canRunControlCenterAction(definition, actor.role).allowed)
          .map(async (definition) => ({
            ...toPublicAction(definition),
            preflight: await evaluateActionPreflight(definition, { actor }),
          })),
      )
    : []
  return {
    schemaVersion: CONTROL_CENTER_ACTION_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    capabilities,
  }
}

function withAdditionalBlocker(
  preflight: ControlCenterActionPreflight,
  blocker: string,
  detail: string,
): ControlCenterActionPreflight {
  return {
    ...preflight,
    status: "blocked",
    executeAllowed: false,
    checks: [...preflight.checks, { id: "dry_run_proof", status: "blocked", detail }],
    blockers: [...new Set([...preflight.blockers, blocker])],
  }
}

async function appendAttemptAudit(input: {
  completedAt: string
  auditId: string
  definition: ActionDefinition
  dryRun: boolean
  actor: ControlCenterActor | null
  authorized: boolean
  ok: boolean
  reason?: string
  output: string
  preflight: ControlCenterActionPreflight
  proofId?: string
  consumedProofId?: string
}): Promise<void> {
  await appendAuditRecord({
    at: input.completedAt,
    audit_id: input.auditId,
    actor: input.actor?.username || "anonymous",
    actor_role: input.actor?.role || "anonymous",
    action: input.definition.id,
    target: input.definition.target,
    risk_class: input.definition.riskClass,
    minimum_role: input.definition.minimumRole,
    dry_run: input.dryRun,
    authorized: input.authorized,
    ok: input.ok,
    reason: redactControlCenterAuditText(input.reason || ""),
    output_preview: redactControlCenterAuditText(input.output),
    preflight_status: input.preflight.status,
    preflight_blockers: input.preflight.blockers,
    ...(input.proofId ? { proof_id: input.proofId } : {}),
    ...(input.consumedProofId ? { consumed_proof_id: input.consumedProofId } : {}),
  })
}

async function executeActionCommand(
  definition: ActionDefinition,
  mode: "dry_run" | "execute",
  reason: string,
): Promise<{ ok: boolean; output: string }> {
  try {
    const command = definition.command(mode, reason)
    const result = await execFileAsync(command.file, command.args, {
      timeout: command.timeout,
      cwd: command.cwd,
      windowsHide: true,
      maxBuffer: 1024 * 1024,
    })
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim() || "Action completed with no output."
    return { ok: true, output: sanitizeControlCenterActionOutput(output) }
  } catch (error) {
    const output = error instanceof Error ? error.message : "Action failed."
    return { ok: false, output: sanitizeControlCenterActionOutput(output) }
  }
}

function issueDryRunProof(actionId: SafeWriteActionId, actor: ControlCenterActor, proofId: string, now = Date.now()): void {
  dryRunProofs.set(proofId, {
    actionId,
    actorUsername: actor.username,
    issuedAt: now,
    expiresAt: now + CONTROL_CENTER_DRY_RUN_PROOF_TTL_MS,
    consumed: false,
  })
}

function consumeDryRunProof(proofId: string): void {
  const proof = dryRunProofs.get(proofId)
  if (proof) proof.consumed = true
}

function requireExactExecutionGate(
  definition: ActionDefinition,
  input: { confirmation?: string; reason?: string },
  preflight: ControlCenterActionPreflight,
): ControlCenterActionPreflight | null {
  if (input.confirmation !== definition.confirmationText) {
    return withAdditionalBlocker(preflight, "confirmation_required", "Enter the exact confirmation text before executing.")
  }
  if (!input.reason || input.reason.trim().length < 8) {
    return withAdditionalBlocker(preflight, "maintenance_reason_required", "Enter a maintenance reason with at least 8 characters.")
  }
  return null
}

export async function runControlCenterAction(input: {
  actionId: string
  confirmation?: string
  reason?: string
  proofId?: string
  dryRun?: boolean
  actor?: ControlCenterActor | null
}): Promise<ControlCenterActionResult> {
  const definition = findActionDefinition(input.actionId)
  if (!definition || !definition.enabled || definition.riskClass !== "safe_write") {
    throw new Error("Unknown or disabled Control Center action.")
  }

  const dryRun = input.dryRun !== false
  const actor = input.actor || null
  const completedAt = new Date().toISOString()
  const identifier = auditId(completedAt, definition.id)
  const access = canRunControlCenterAction(definition, actor?.role)
  let preflight = await evaluateActionPreflight(definition, { actor, proofId: input.proofId })

  if (!access.allowed) {
    await appendAttemptAudit({
      completedAt,
      auditId: identifier,
      definition,
      dryRun,
      actor,
      authorized: false,
      ok: false,
      reason: input.reason,
      output: access.reason,
      preflight,
    })
    throw new ControlCenterAuthorizationError(access.reason, actor ? 403 : 401)
  }

  if (dryRun && !preflight.dryRunAllowed) {
    await appendAttemptAudit({
      completedAt,
      auditId: identifier,
      definition,
      dryRun: true,
      actor,
      authorized: true,
      ok: false,
      reason: input.reason,
      output: "Dry-run preflight is not ready.",
      preflight,
    })
    throw new ControlCenterPreflightError("Dry-run preflight is not ready.", preflight)
  }

  if (!dryRun) {
    const confirmationGate = requireExactExecutionGate(definition, input, preflight)
    if (confirmationGate) {
      await appendAttemptAudit({
        completedAt,
        auditId: identifier,
        definition,
        dryRun: false,
        actor,
        authorized: true,
        ok: false,
        reason: input.reason,
        output: "Execution confirmation gate is not ready.",
        preflight: confirmationGate,
      })
      throw new ControlCenterPreflightError("Execution confirmation gate is not ready.", confirmationGate)
    }
    if (!preflight.executeAllowed || !input.proofId) {
      await appendAttemptAudit({
        completedAt,
        auditId: identifier,
        definition,
        dryRun: false,
        actor,
        authorized: true,
        ok: false,
        reason: input.reason,
        output: "Execution requires a current dry-run proof.",
        preflight,
      })
      throw new ControlCenterPreflightError("Execution requires a current dry-run proof.", preflight)
    }
    consumeDryRunProof(input.proofId)
    const executed = await executeActionCommand(definition, "execute", input.reason || "")
    preflight = await evaluateActionPreflight(definition, { actor, proofId: input.proofId })
    const result: ControlCenterActionResult = {
      action: toPublicAction(definition),
      dryRun: false,
      ok: executed.ok,
      output: executed.output,
      auditId: identifier,
      completedAt,
      preflight,
    }
    await appendAttemptAudit({
      completedAt,
      auditId: identifier,
      definition,
      dryRun: false,
      actor,
      authorized: true,
      ok: result.ok,
      reason: input.reason,
      output: result.output,
      preflight,
      consumedProofId: input.proofId,
    })
    return result
  }

  const nativeResult = definition.nativeDryRun
    ? await executeActionCommand(definition, "dry_run", input.reason || "")
    : { ok: true, output: "Dry-run preflight completed." }
  const proofId = nativeResult.ok && actor ? randomUUID() : undefined
  await appendAttemptAudit({
    completedAt,
    auditId: identifier,
    definition,
    dryRun: true,
    actor,
    authorized: true,
    ok: nativeResult.ok,
    reason: input.reason,
    output: nativeResult.output,
    preflight,
    proofId,
  })
  if (proofId && actor) {
    issueDryRunProof(definition.id, actor, proofId)
    preflight = await evaluateActionPreflight(definition, { actor, proofId })
  }
  const result: ControlCenterActionResult = {
    action: toPublicAction(definition),
    dryRun: true,
    ok: nativeResult.ok,
    output: nativeResult.output,
    auditId: identifier,
    completedAt,
    proofId,
    preflight,
  }
  return result
}

export function projectControlCenterActionResult(result: ControlCenterActionResult): ControlCenterActionResultProjection {
  return {
    schemaVersion: CONTROL_CENTER_ACTION_SCHEMA_VERSION,
    actionId: result.action.id,
    dryRun: result.dryRun,
    ok: result.ok,
    status: result.ok ? (result.dryRun ? "dry_run_validated" : "completed") : "failed",
    auditId: result.auditId,
    completedAt: result.completedAt,
    ...(result.proofId ? { proofId: result.proofId } : {}),
    preflight: result.preflight,
    message: result.ok
      ? result.dryRun
        ? "Dry-run validation completed."
        : "Bounded local refresh completed."
      : "Bounded local refresh failed. Review the local audit evidence.",
  }
}

/** Test-only reset; production code never exposes proof inventory to the browser. */
export function clearControlCenterActionProofsForTest(): void {
  dryRunProofs.clear()
}

async function appendAuditRecord(record: AuditRecord): Promise<void> {
  const auditPath = getControlCenterEvidenceConfig().actionAuditPath
  const auditDir = path.dirname(auditPath)
  await mkdir(auditDir, { recursive: true })
  await appendFile(auditPath, `${JSON.stringify(record)}\n`, "utf-8")
}
