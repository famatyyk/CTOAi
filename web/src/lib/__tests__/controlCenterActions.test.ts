import { afterEach, describe, expect, it, vi } from "vitest"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import {
  CONTROL_CENTER_ACTION_READINESS_TTL_MS,
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

const actionMcpTools: Record<(typeof actionIds)[number], string> = {
  "repo-hygiene-refresh": "ctoai_repo_hygiene_refresh",
  "api-cost-refresh": "ctoai_api_cost_refresh",
  "evidence-pack-refresh": "ctoai_evidence_pack_refresh",
  "engine-brain-refresh": "ctoai_engine_brain_refresh",
  "p7-cockpit-smoke-refresh": "ctoai_p7_cockpit_smoke_refresh",
  "roadmap-state-refresh": "ctoai_roadmap_state_refresh",
  "full-workspace-validation-refresh": "ctoai_full_workspace_validation_refresh",
}

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

function readinessOutputPath(root: string, filename: string) {
  return path.join(root, "AI", "generated", filename)
}

function readyP7ActionReadinessPayload(generatedAt: string): Record<string, unknown> {
  return {
    schema_version: 1,
    generated_at: generatedAt,
    status: "safe_write_tools_enabled",
    candidate_count: actionIds.length,
    mcp_write_tool_count: actionIds.length,
    mcp_write_tools: actionIds.map((actionId) => actionMcpTools[actionId]),
    enabled_safe_write_tools: actionIds.map((action_id) => ({
      action_id,
      mcp_tool: actionMcpTools[action_id],
      risk_class: "safe_write",
    })),
    safe_write_candidates: actionIds.map((id) => ({
      id,
      risk_class: "safe_write",
      control_center_enabled: true,
      risk_model_present: true,
      plugin_mcp_allowed: true,
      audit_ready: true,
      expected_mcp_tool: actionMcpTools[id],
      missing_gates: [],
    })),
  }
}

function writeReadyP6Readiness(root: string, generatedAt: string) {
  const outputPath = readinessOutputPath(root, "P6_CODEX_INTEGRATION_READINESS.json")
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(
    outputPath,
    JSON.stringify({
      schema_version: 1,
      generated_at: generatedAt,
      status: "ready_for_plugin_design",
      checks: [{ name: "fixture_p6_contract", status: "passed" }],
    }),
  )
}

function writeP7ActionReadiness(root: string, payload: Record<string, unknown> | string) {
  const outputPath = readinessOutputPath(root, "P7_ACTION_READINESS.json")
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })
  fs.writeFileSync(outputPath, typeof payload === "string" ? payload : JSON.stringify(payload))
}

function writeReadyP7ActionReadiness(root: string, generatedAt: string) {
  writeP7ActionReadiness(root, readyP7ActionReadinessPayload(generatedAt))
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
  const generatedAt = new Date().toISOString()
  writeReadyP6Readiness(root, generatedAt)
  writeReadyP7ActionReadiness(root, generatedAt)
  writeActionScripts(root, evidenceScript)
  process.chdir(root)
  process.env.CTOA_WORKSPACE_ROOT = root
  process.env.CTOA_PYTHON_BIN = process.execPath
  process.env.CTOA_ACTION_AUDIT_PATH = auditPath
  process.env.CTOA_REPO_ROOT = root
  return { root, auditPath, generatedAt }
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

  it("does not issue a proof for an undated synthetic enabled P7 artifact", async () => {
    const { root, auditPath, generatedAt } = setupReadyWorkspace()
    const payload = readyP7ActionReadinessPayload(generatedAt)
    delete payload.generated_at
    writeP7ActionReadiness(root, payload)

    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining(["p7_action_readiness_generated_at_invalid"]) },
    })

    const [audit] = readAudit(auditPath)
    expect(audit.proof_id).toBeUndefined()
  })

  it.each([
    ["malformed", "{", "p7_action_readiness_missing"],
    ["duplicate-key", "duplicate", "p7_action_readiness_missing"],
  ])("does not issue a proof for %s P7 readiness JSON", async (_label, serialized, blocker) => {
    const { root, generatedAt } = setupReadyWorkspace()
    const payload = readyP7ActionReadinessPayload(generatedAt)
    const body =
      serialized === "duplicate"
        ? JSON.stringify(payload).replace('"schema_version":1', '"schema_version":1,"schema_version":1')
        : serialized
    writeP7ActionReadiness(root, body)

    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining([blocker]) },
    })
  })

  it("requires fresh P6/P7 timestamps from the same snapshot instant", async () => {
    const { root, generatedAt } = setupReadyWorkspace()
    writeReadyP7ActionReadiness(root, new Date(Date.parse(generatedAt) - 1000).toISOString())

    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining(["p6_p7_readiness_snapshot_mismatch"]) },
    })

    const freshP6At = new Date().toISOString()
    writeReadyP6Readiness(root, freshP6At)
    writeReadyP7ActionReadiness(root, new Date(Date.now() - CONTROL_CENTER_ACTION_READINESS_TTL_MS - 1).toISOString())
    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining(["p7_action_readiness_stale"]) },
    })
  })

  it("requires an all-passed P6 binding and audit-ready evidence for every action", async () => {
    const { root, generatedAt } = setupReadyWorkspace()
    const p6Path = readinessOutputPath(root, "P6_CODEX_INTEGRATION_READINESS.json")
    fs.writeFileSync(
      p6Path,
      JSON.stringify({
        schema_version: 1,
        generated_at: generatedAt,
        status: "ready_for_plugin_design",
        checks: [{ name: "fixture_p6_contract", status: "blocked" }],
      }),
    )
    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining(["p6_action_readiness_checks_incomplete"]) },
    })

    writeReadyP6Readiness(root, generatedAt)
    const payload = readyP7ActionReadinessPayload(generatedAt)
    const candidates = payload.safe_write_candidates as Array<Record<string, unknown>>
    candidates.find((candidate) => candidate.id === "evidence-pack-refresh")!.audit_ready = false
    candidates.find((candidate) => candidate.id === "evidence-pack-refresh")!.missing_gates = ["current_audit_missing"]
    writeP7ActionReadiness(root, payload)
    await expect(runControlCenterAction({ actionId: "evidence-pack-refresh", dryRun: true, actor: operator })).rejects.toMatchObject({
      statusCode: 409,
      preflight: { blockers: expect.arrayContaining(["p7_action_audit_binding_incomplete"]) },
    })
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
    const generatedAt = new Date().toISOString()
    writeReadyP6Readiness(root, generatedAt)
    writeReadyP7ActionReadiness(root, generatedAt)
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
