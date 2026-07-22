import { afterEach, describe, expect, it, vi } from "vitest"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import {
  CONTROL_CENTER_ACTION_SCHEMA_VERSION,
  ControlCenterPreflightError,
  clearControlCenterActionProofsForTest,
  listControlCenterActionCapabilities,
  redactControlCenterAuditText,
  resolveControlCenterPython,
  resolveControlCenterWorkspaceFile,
  resolveControlCenterWorkspaceRoot,
  runControlCenterAction,
  sanitizeControlCenterActionOutput,
} from "../controlCenterActions"
import { canRunControlCenterAction } from "../controlCenterPolicy"

const originalCwd = process.cwd()
const originalWorkspaceRoot = process.env.CTOA_WORKSPACE_ROOT
const originalPythonBin = process.env.CTOA_PYTHON_BIN
const originalRepoRoot = process.env.CTOA_REPO_ROOT
const originalActionAuditPath = process.env.CTOA_ACTION_AUDIT_PATH

const operator = { username: "operator-one", displayName: "Operator One", role: "operator" as const }
const anotherOperator = { username: "operator-two", displayName: "Operator Two", role: "operator" as const }
const actionIds = [
  "repo-hygiene-refresh",
  "api-cost-refresh",
  "evidence-pack-refresh",
  "engine-brain-refresh",
  "p7-cockpit-smoke-refresh",
  "roadmap-state-refresh",
  "full-workspace-validation-refresh",
] as const

afterEach(() => {
  process.chdir(originalCwd)
  if (originalWorkspaceRoot === undefined) delete process.env.CTOA_WORKSPACE_ROOT
  else process.env.CTOA_WORKSPACE_ROOT = originalWorkspaceRoot
  if (originalPythonBin === undefined) delete process.env.CTOA_PYTHON_BIN
  else process.env.CTOA_PYTHON_BIN = originalPythonBin
  if (originalRepoRoot === undefined) delete process.env.CTOA_REPO_ROOT
  else process.env.CTOA_REPO_ROOT = originalRepoRoot
  if (originalActionAuditPath === undefined) delete process.env.CTOA_ACTION_AUDIT_PATH
  else process.env.CTOA_ACTION_AUDIT_PATH = originalActionAuditPath
  clearControlCenterActionProofsForTest()
  vi.unstubAllEnvs()
})

function writeReadyP7ActionReadiness(root: string) {
  const outputPath = path.join(root, "AI", "generated", "P7_ACTION_READINESS.json")
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(
    outputPath,
    JSON.stringify({
      schema_version: 1,
      status: "safe_write_tools_enabled",
      candidate_count: actionIds.length,
      mcp_write_tool_count: actionIds.length,
      enabled_safe_write_tools: actionIds.map((action_id) => ({ action_id, risk_class: "safe_write" })),
      safe_write_candidates: actionIds.map((id) => ({
        id,
        risk_class: "safe_write",
        control_center_enabled: true,
        plugin_mcp_allowed: true,
      })),
    }),
  )
}

function writeActionScripts(root: string, evidenceScript = "console.log('safe action completed')") {
  const scripts: Record<string, string> = {
    "repo_hygiene_audit.py": "console.log('repo hygiene completed')",
    "api_cost_report.py": "console.log('api cost completed')",
    "release_evidence_pack.py": evidenceScript,
    "engine_brain_index.py": "console.log('engine brain completed')",
    "control_center_p7_cockpit_smoke.py": "console.log('p7 smoke completed')",
    "ctoai_roadmap_state.py": "console.log('roadmap native dry run completed')",
    "ctoa_full_workspace_validation.py": "console.log('full workspace validation native dry run completed')",
  }
  const scriptsDir = path.join(root, "scripts", "ops")
  fs.mkdirSync(scriptsDir, { recursive: true })
  for (const [name, contents] of Object.entries(scripts)) {
    fs.writeFileSync(path.join(scriptsDir, name), contents)
  }
}

function setupReadyWorkspace(evidenceScript?: string) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
  const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
  writeReadyP7ActionReadiness(root)
  writeActionScripts(root, evidenceScript)
  process.chdir(root)
  process.env.CTOA_WORKSPACE_ROOT = root
  process.env.CTOA_PYTHON_BIN = process.execPath
  process.env.CTOA_ACTION_AUDIT_PATH = auditPath
  process.env.CTOA_REPO_ROOT = root
  return { root, auditPath }
}

function readAudit(auditPath: string) {
  return fs
    .readFileSync(auditPath, "utf-8")
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line) as Record<string, unknown>)
}

describe("control center action capability engine", () => {
  it("redacts common secret forms before audit persistence", () => {
    const text = redactControlCenterAuditText(
      "Bearer abcdefghijklmnopqrstuvwxyz token=secret-token-value password=hunter2 sk-secret-should-not-leak {\"password\":\"json-password-value\",\"access_token\":\"json-token-value\"} api_key='quoted-api-key-value'",
    )

    expect(text).toContain("Bearer [redacted]")
    expect(text).toContain("token=[redacted]")
    expect(text).toContain("password=[redacted]")
    expect(text).toContain('"password":"[redacted]"')
    expect(text).toContain('"access_token":"[redacted]"')
    expect(text).toContain("api_key='[redacted]'")
    expect(text).not.toContain("secret-token-value")
    expect(text).not.toContain("hunter2")
  })

  it("sanitizes action output before browser display", () => {
    vi.stubEnv("CTOA_REPO_ROOT", "C:\\repo\\CTOAi")
    const output = sanitizeControlCenterActionOutput(
      [
        "Wrote C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
        "Runtime C:\\repo\\CTOAi\\runtime\\evidence\\latest.json",
        "Temp file /tmp/ctoa/action-output/latest.json",
        "token=secret-token-value password=legacy-password-value",
      ].join("\n"),
    )

    expect(output).toContain("[external]/client")
    expect(output).toContain("runtime/evidence/latest.json")
    expect(output).toContain("token=[redacted]")
    expect(output).not.toContain("C:\\Users\\zycie")
    expect(output).not.toContain("secret-token-value")
  })

  it("requires operator role for local refresh actions", () => {
    const action = { minimumRole: "operator" as const }
    expect(canRunControlCenterAction(action, null).allowed).toBe(false)
    expect(canRunControlCenterAction(action, "member").allowed).toBe(false)
    expect(canRunControlCenterAction(action, "operator").allowed).toBe(true)
  })

  it("uses repo-local virtualenv python when no explicit python is configured", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const localPython = process.platform === "win32" ? path.join(root, ".venv", "Scripts", "python.exe") : path.join(root, ".venv", "bin", "python")
    fs.mkdirSync(path.dirname(localPython), { recursive: true })
    fs.writeFileSync(localPython, "")
    vi.stubEnv("CTOA_PYTHON_BIN", "")
    expect(resolveControlCenterPython(root)).toBe(localPython)
  })

  it("resolves workspace files only inside the configured root", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const scriptPath = path.join(root, "scripts", "ops", "repo_hygiene_audit.py")
    fs.mkdirSync(path.dirname(scriptPath), { recursive: true })
    fs.writeFileSync(scriptPath, "print('ok')\n")
    expect(resolveControlCenterWorkspaceFile(root, "scripts/ops/repo_hygiene_audit.py")).toBe(fs.realpathSync(scriptPath))
    expect(() => resolveControlCenterWorkspaceFile(root, "../outside.py")).toThrow(/escapes the workspace root/)
    expect(() => resolveControlCenterWorkspaceFile(root, path.join(root, "absolute.py"))).toThrow(/repo-relative paths/)
  })

  it("resolves the current repository root from a web cwd", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const web = path.join(root, "web")
    fs.mkdirSync(web)
    process.chdir(web)
    vi.stubEnv("CTOA_WORKSPACE_ROOT", "")
    expect(resolveControlCenterWorkspaceRoot()).toBe(root)
  })

  it("publishes schema-v2 capabilities without command or filesystem details", async () => {
    const { root } = setupReadyWorkspace()
    const payload = await listControlCenterActionCapabilities({ actor: operator })
    const serialized = JSON.stringify(payload)

    expect(payload.schemaVersion).toBe(CONTROL_CENTER_ACTION_SCHEMA_VERSION)
    expect(payload.capabilities).toHaveLength(7)
    expect(payload.capabilities.find((item) => item.id === "roadmap-state-refresh")?.nativeDryRun).toBe(true)
    expect(payload.capabilities.find((item) => item.id === "full-workspace-validation-refresh")?.nativeDryRun).toBe(true)
    expect(payload.capabilities.every((item) => item.executionMode === "dry_run_first")).toBe(true)
    expect(serialized).not.toContain("commandSummary")
    expect(serialized).not.toContain("scripts/ops")
    expect(serialized).not.toContain(root)
    expect(serialized).not.toContain(operator.username)
    expect(serialized).not.toContain(operator.displayName)
  })

  it("audits a denied request before any local action runs", async () => {
    const { auditPath } = setupReadyWorkspace()
    await expect(
      runControlCenterAction({
        actionId: "evidence-pack-refresh",
        dryRun: true,
        actor: { username: "member", displayName: "Member", role: "member" },
      }),
    ).rejects.toMatchObject({ statusCode: 403 })

    const [audit] = readAudit(auditPath)
    expect(audit.authorized).toBe(false)
    expect(audit.action).toBe("evidence-pack-refresh")
  })

  it("runs roadmap-state-refresh through its native dry-run and records a proof", async () => {
    const { auditPath } = setupReadyWorkspace()
    const result = await runControlCenterAction({ actionId: "roadmap-state-refresh", dryRun: true, actor: operator })

    expect(result.ok).toBe(true)
    expect(result.output).toContain("roadmap native dry run completed")
    expect(result.proofId).toBeTruthy()
    expect(result.preflight.executeAllowed).toBe(true)
    const [audit] = readAudit(auditPath)
    expect(audit.proof_id).toBe(result.proofId)
    expect(audit.dry_run).toBe(true)
  })

  it("runs full-workspace-validation-refresh through native dry-run and requires its exact confirmation", async () => {
    const { auditPath } = setupReadyWorkspace()
    const dryRun = await runControlCenterAction({
      actionId: "full-workspace-validation-refresh",
      dryRun: true,
      actor: operator,
    })

    expect(dryRun.ok).toBe(true)
    expect(dryRun.output).toContain("full workspace validation native dry run completed")
    expect(dryRun.proofId).toBeTruthy()
    expect(dryRun.preflight.executeAllowed).toBe(true)

    await expect(
      runControlCenterAction({
        actionId: "full-workspace-validation-refresh",
        dryRun: false,
        proofId: dryRun.proofId,
        confirmation: "refresh validation",
        reason: "Refresh full workspace validation evidence",
        actor: operator,
      }),
    ).rejects.toBeInstanceOf(ControlCenterPreflightError)

    const completed = await runControlCenterAction({
      actionId: "full-workspace-validation-refresh",
      dryRun: false,
      proofId: dryRun.proofId,
      confirmation: "refresh full workspace validation",
      reason: "Refresh full workspace validation evidence",
      actor: operator,
    })
    const audit = readAudit(auditPath)

    expect(completed.ok).toBe(true)
    expect(completed.dryRun).toBe(false)
    expect(audit.some((item) => item.action === "full-workspace-validation-refresh" && item.risk_class === "safe_write")).toBe(true)
    expect(audit.some((item) => item.consumed_proof_id === dryRun.proofId)).toBe(true)
  })

  it("does not let another operator reuse an actor-bound dry-run", async () => {
    setupReadyWorkspace()
    const dryRun = await runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })
    await expect(
      runControlCenterAction({
        actionId: "evidence-pack-refresh",
        dryRun: false,
        proofId: dryRun.proofId,
        confirmation: "refresh evidence pack",
        reason: "Refresh evidence after review",
        actor: anotherOperator,
      }),
    ).rejects.toBeInstanceOf(ControlCenterPreflightError)
  })

  it("executes after dry-run, sanitizes output, and consumes the proof", async () => {
    const { auditPath } = setupReadyWorkspace(
      [
        "console.log('Completed token=secret-token-value password=legacy-password-value')",
        "console.log('Live client C:\\\\Users\\\\zycie\\\\AppData\\\\Local\\\\Solteria\\\\client')",
      ].join("\n"),
    )
    const dryRun = await runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })
    const result = await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: false,
      proofId: dryRun.proofId,
      confirmation: "refresh evidence pack",
      reason: "Refresh evidence after review",
      actor: operator,
    })

    expect(result.ok).toBe(true)
    expect(result.output).toContain("token=[redacted]")
    expect(result.output).toContain("password=[redacted]")
    expect(result.output).toContain("[external]/client")
    expect(result.output).not.toContain("secret-token-value")
    await expect(
      runControlCenterAction({
        actionId: "evidence-pack-refresh",
        dryRun: false,
        proofId: dryRun.proofId,
        confirmation: "refresh evidence pack",
        reason: "Refresh evidence after review",
        actor: operator,
      }),
    ).rejects.toBeInstanceOf(ControlCenterPreflightError)

    const audit = readAudit(auditPath)
    expect(audit.some((item) => item.consumed_proof_id === dryRun.proofId)).toBe(true)
    expect(JSON.stringify(audit)).not.toContain("secret-token-value")
  })

  it("fails closed and records a preflight audit when trusted runtime is unavailable", async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    writeReadyP7ActionReadiness(root)
    writeActionScripts(root)
    process.chdir(root)
    process.env.CTOA_WORKSPACE_ROOT = root
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    vi.stubEnv("CTOA_PYTHON_BIN", "")

    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toBeInstanceOf(
      ControlCenterPreflightError,
    )
    const [audit] = readAudit(auditPath)
    expect(audit.ok).toBe(false)
    expect(audit.preflight_blockers).toContain("trusted_runtime_unavailable")
  })
})
