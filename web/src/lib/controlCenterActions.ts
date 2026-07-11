import { execFile } from "node:child_process"
import { lstatSync, realpathSync, statSync } from "node:fs"
import { appendFile, mkdir } from "node:fs/promises"
import path from "node:path"
import { promisify } from "node:util"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"
import type { ControlCenterRole, ControlCenterRiskClass } from "@/lib/controlCenterPolicy"
import { canRunControlCenterAction, minimumRoleForRiskClass } from "@/lib/controlCenterPolicy"
import { redactControlCenterAuditText as redactAuditText } from "@/lib/controlCenterRedaction"

const execFileAsync = promisify(execFile)

export type ControlCenterActor = {
  username: string
  displayName: string
  role: ControlCenterRole
}

export type ControlCenterAction = {
  id: string
  label: string
  description: string
  target: "local"
  riskClass: ControlCenterRiskClass
  minimumRole: ControlCenterRole
  confirmationText?: string
  requiresReason: boolean
  dryRunAvailable: boolean
  enabled: boolean
  commandSummary: string
}

export type ControlCenterActionResult = {
  action: ControlCenterAction
  dryRun: boolean
  ok: boolean
  output: string
  auditId: string
  completedAt: string
}

type CommandSpec = {
  file: string
  args: string[]
  cwd?: string
  timeout: number
}

type ActionDefinition = ControlCenterAction & {
  command: () => CommandSpec
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
}

export class ControlCenterAuthorizationError extends Error {
  statusCode: number

  constructor(message: string, statusCode = 403) {
    super(message)
    this.name = "ControlCenterAuthorizationError"
    this.statusCode = statusCode
  }
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
      description: "Rebuild the local repo hygiene report from the current workspace tree.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      requiresReason: false,
      dryRunAvailable: true,
      enabled: true,
      commandSummary: "python scripts/ops/repo_hygiene_audit.py --json-out runtime/repo-hygiene/local-pr-quality.json",
      command: () =>
        pythonCommand("scripts/ops/repo_hygiene_audit.py", ["--json-out", "runtime/repo-hygiene/local-pr-quality.json"], 120000),
    },
    {
      id: "api-cost-refresh",
      label: "Refresh API cost report",
      description: "Rebuild the local API cost report from the current eval run artifacts.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      requiresReason: false,
      dryRunAvailable: true,
      enabled: true,
      commandSummary:
        "python scripts/ops/api_cost_report.py --json-out runtime/api-cost/latest.json --md-out runtime/api-cost/latest.md",
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
      description: "Rebuild the compact evidence pack that Control Center reads for sign-off.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      requiresReason: false,
      dryRunAvailable: true,
      enabled: true,
      commandSummary:
        "python scripts/ops/release_evidence_pack.py --json-out runtime/evidence/latest.json --md-out runtime/evidence/latest.md",
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
      description: "Regenerate the local Engine Brain context files under AI/generated.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      requiresReason: false,
      dryRunAvailable: true,
      enabled: true,
      commandSummary: "python scripts/ops/engine_brain_index.py",
      command: () => pythonCommand("scripts/ops/engine_brain_index.py", [], 180000),
    },
    {
      id: "p7-cockpit-smoke-refresh",
      label: "Refresh P7 cockpit smoke",
      description: "Regenerate the local P7 cockpit smoke evidence from Engine Brain, release evidence, and action audit state.",
      target: "local",
      riskClass: "safe_write",
      minimumRole: minimumRoleForRiskClass("safe_write"),
      requiresReason: false,
      dryRunAvailable: true,
      enabled: true,
      commandSummary: "python scripts/ops/control_center_p7_cockpit_smoke.py",
      command: () => pythonCommand("scripts/ops/control_center_p7_cockpit_smoke.py", [], 180000),
    },
  ]
}

export function listControlCenterActions(): ControlCenterAction[] {
  return actionCatalog().map(({ command, ...action }) => {
    void command
    return action
  })
}

export function getControlCenterAction(actionId: string): ControlCenterAction | null {
  const action = listControlCenterActions().find((item) => item.id === actionId)
  return action || null
}

export async function runControlCenterAction(input: {
  actionId: string
  confirmation?: string
  reason?: string
  dryRun?: boolean
  actor?: ControlCenterActor | null
}): Promise<ControlCenterActionResult> {
  const definition = actionCatalog().find((item) => item.id === input.actionId)
  if (!definition) {
    throw new Error(`Unknown Control Center action: ${input.actionId}`)
  }
  if (!definition.enabled || definition.riskClass === "forbidden_ui") {
    throw new Error(`Action is not enabled in Control Center: ${definition.id}`)
  }

  const dryRun = Boolean(input.dryRun)
  const actor = input.actor || null
  const access = canRunControlCenterAction(definition, actor?.role)
  const completedAt = new Date().toISOString()
  const auditId = `${completedAt.replace(/[^0-9]/g, "")}-${definition.id}`

  if (!access.allowed) {
    const output = access.reason
    await appendAuditRecord({
      at: completedAt,
      audit_id: auditId,
      actor: actor?.username || "anonymous",
      actor_role: actor?.role || "anonymous",
      action: definition.id,
      target: definition.target,
      risk_class: definition.riskClass,
      minimum_role: definition.minimumRole,
      dry_run: dryRun,
      authorized: false,
      ok: false,
      reason: redactControlCenterAuditText(input.reason || ""),
      output_preview: redactControlCenterAuditText(output),
    })
    throw new ControlCenterAuthorizationError(output, actor ? 403 : 401)
  }

  if (definition.riskClass === "guarded_write" || definition.riskClass === "dangerous") {
    if (definition.confirmationText && input.confirmation !== definition.confirmationText) {
      throw new Error(`Confirmation text must match: ${definition.confirmationText}`)
    }
    if (definition.requiresReason && (!input.reason || input.reason.trim().length < 8)) {
      throw new Error("A maintenance reason with at least 8 characters is required.")
    }
  }

  let ok = true
  let output = dryRun ? `DRY RUN ONLY\n${definition.commandSummary}` : ""

  if (!dryRun) {
    try {
      const command = definition.command()
      const result = await execFileAsync(command.file, command.args, {
        timeout: command.timeout,
        cwd: command.cwd,
        windowsHide: true,
        maxBuffer: 1024 * 1024,
      })
      output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim() || "Action completed with no output."
    } catch (error) {
      ok = false
      output = error instanceof Error ? error.message : "Action failed."
    }
  }

  output = sanitizeControlCenterActionOutput(output)

  const { command, ...action } = definition
  void command
  const result = { action, dryRun, ok, output, auditId, completedAt }
  await appendAuditRecord({
    at: result.completedAt,
    audit_id: result.auditId,
    actor: actor?.username || "anonymous",
    actor_role: actor?.role || "anonymous",
    action: result.action.id,
    target: result.action.target,
    risk_class: result.action.riskClass,
    minimum_role: result.action.minimumRole,
    dry_run: result.dryRun,
    authorized: true,
    ok: result.ok,
    reason: redactControlCenterAuditText(input.reason || ""),
    output_preview: redactControlCenterAuditText(result.output),
  })
  return result
}

async function appendAuditRecord(record: AuditRecord): Promise<void> {
  const auditPath = getControlCenterEvidenceConfig().actionAuditPath
  const auditDir = path.dirname(auditPath)
  await mkdir(auditDir, { recursive: true })
  await appendFile(auditPath, `${JSON.stringify(record)}\n`, "utf-8")
}
