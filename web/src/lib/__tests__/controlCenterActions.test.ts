import { afterEach, describe, expect, it, vi } from "vitest"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"
import {
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

afterEach(() => {
  process.chdir(originalCwd)
  if (originalWorkspaceRoot === undefined) {
    delete process.env.CTOA_WORKSPACE_ROOT
  } else {
    process.env.CTOA_WORKSPACE_ROOT = originalWorkspaceRoot
  }
  if (originalPythonBin === undefined) {
    delete process.env.CTOA_PYTHON_BIN
  } else {
    process.env.CTOA_PYTHON_BIN = originalPythonBin
  }
  if (originalRepoRoot === undefined) {
    delete process.env.CTOA_REPO_ROOT
  } else {
    process.env.CTOA_REPO_ROOT = originalRepoRoot
  }
  if (originalActionAuditPath === undefined) {
    delete process.env.CTOA_ACTION_AUDIT_PATH
  } else {
    process.env.CTOA_ACTION_AUDIT_PATH = originalActionAuditPath
  }
  vi.unstubAllEnvs()
})

describe("control center action permissions", () => {
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
    expect(text).not.toContain("sk-secret-should-not-leak")
    expect(text).not.toContain("json-password-value")
    expect(text).not.toContain("json-token-value")
    expect(text).not.toContain("quoted-api-key-value")
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
    expect(output).toContain("[external]/latest.json")
    expect(output).toContain("token=[redacted]")
    expect(output).toContain("password=[redacted]")
    expect(output).not.toContain("C:\\Users\\zycie")
    expect(output).not.toContain("C:\\repo\\CTOAi")
    expect(output).not.toContain("/tmp/ctoa")
    expect(output).not.toContain("secret-token-value")
    expect(output).not.toContain("legacy-password-value")
  })

  it("requires operator role for local refresh actions", () => {
    const action = { minimumRole: "operator" as const }

    expect(canRunControlCenterAction(action, null)).toEqual({
      allowed: false,
      requiredRole: "operator",
      reason: "Sign in to run Control Center actions.",
    })
    expect(canRunControlCenterAction(action, "member")).toEqual({
      allowed: false,
      requiredRole: "operator",
      reason: "Operator role required for this action.",
    })
    expect(canRunControlCenterAction(action, "operator")).toEqual({
      allowed: true,
      requiredRole: "operator",
      reason: "",
    })
  })

  it("uses repo-local virtualenv python when no explicit python is configured", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const localPython =
      process.platform === "win32"
        ? path.join(tmpRoot, ".venv", "Scripts", "python.exe")
        : path.join(tmpRoot, ".venv", "bin", "python")
    fs.mkdirSync(path.dirname(localPython), { recursive: true })
    fs.writeFileSync(localPython, "")
    vi.stubEnv("CTOA_PYTHON_BIN", "")

    expect(resolveControlCenterPython(tmpRoot)).toBe(localPython)
  })

  it("resolves workspace root from repo cwd without climbing above the repo", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    process.chdir(tmpRoot)
    vi.stubEnv("CTOA_WORKSPACE_ROOT", "")

    expect(resolveControlCenterWorkspaceRoot()).toBe(tmpRoot)
  })

  it("resolves workspace root from web cwd to the repo parent", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const webDir = path.join(tmpRoot, "web")
    fs.mkdirSync(webDir)
    process.chdir(webDir)
    vi.stubEnv("CTOA_WORKSPACE_ROOT", "")

    expect(resolveControlCenterWorkspaceRoot()).toBe(tmpRoot)
  })

  it("requires explicit workspace root overrides to be absolute existing directories", () => {
    vi.stubEnv("CTOA_WORKSPACE_ROOT", "relative-workspace")

    expect(() => resolveControlCenterWorkspaceRoot()).toThrow(/absolute path/)
  })

  it("keeps action scripts inside the workspace root", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const scriptPath = path.join(tmpRoot, "scripts", "ops", "repo_hygiene_audit.py")
    fs.mkdirSync(path.dirname(scriptPath), { recursive: true })
    fs.writeFileSync(scriptPath, "print('ok')\n")

    expect(resolveControlCenterWorkspaceFile(tmpRoot, "scripts/ops/repo_hygiene_audit.py")).toBe(
      fs.realpathSync(scriptPath),
    )
    expect(() => resolveControlCenterWorkspaceFile(tmpRoot, "../outside.py")).toThrow(/escapes the workspace root/)
    expect(() => resolveControlCenterWorkspaceFile(tmpRoot, path.join(tmpRoot, "absolute.py"))).toThrow(
      /repo-relative paths/,
    )
  })

  it("rejects action scripts that resolve outside the workspace through symlinked parents", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const outsideRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-outside-"))
    const outsideScript = path.join(outsideRoot, "repo_hygiene_audit.py")
    const scriptsDir = path.join(tmpRoot, "scripts")
    const linkedOpsDir = path.join(scriptsDir, "ops")
    fs.mkdirSync(scriptsDir, { recursive: true })
    fs.writeFileSync(outsideScript, "print('outside')\n")

    try {
      fs.symlinkSync(outsideRoot, linkedOpsDir, process.platform === "win32" ? "junction" : "dir")
    } catch {
      return
    }

    expect(() => resolveControlCenterWorkspaceFile(tmpRoot, "scripts/ops/repo_hygiene_audit.py")).toThrow(
      /outside the workspace root/,
    )
  })

  it("requires explicit python overrides to be absolute paths", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    vi.stubEnv("CTOA_PYTHON_BIN", "python")

    expect(() => resolveControlCenterPython(tmpRoot)).toThrow(/absolute path/)
  })

  it("accepts an existing absolute python override", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const configuredPython = path.join(tmpRoot, "python.exe")
    fs.writeFileSync(configuredPython, "")
    vi.stubEnv("CTOA_PYTHON_BIN", configuredPython)

    expect(resolveControlCenterPython(tmpRoot)).toBe(configuredPython)
  })

  it("rejects configured python overrides that are directories", () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const configuredPython = path.join(tmpRoot, "python-dir")
    fs.mkdirSync(configuredPython)
    vi.stubEnv("CTOA_PYTHON_BIN", configuredPython)

    expect(() => resolveControlCenterPython(tmpRoot)).toThrow(/existing file/)
  })

  it("writes a denied audit record when the actor lacks permission", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot

    await expect(
      runControlCenterAction({
        actionId: "evidence-pack-refresh",
        dryRun: true,
        actor: { username: "strategos", displayName: "Strategos", role: "member" },
      }),
    ).rejects.toMatchObject({ statusCode: 403 })

    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.authorized).toBe(false)
    expect(audit.actor_role).toBe("member")
    expect(audit.action).toBe("evidence-pack-refresh")
  })

  it("fails closed and audits failure when no trusted python is available", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot
    vi.stubEnv("CTOA_PYTHON_BIN", "")

    const result = await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: false,
      actor: { username: "famatyyk", displayName: "Famatyyk", role: "operator" },
    })

    expect(result.ok).toBe(false)
    expect(result.output).toContain("Trusted Python executable not found")
    expect(result.output).not.toContain(tmpRoot)

    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.authorized).toBe(true)
    expect(audit.ok).toBe(false)
    expect(audit.output_preview).toContain("Trusted Python executable not found")
    expect(audit.output_preview).not.toContain(tmpRoot)
  })

  it("fails closed and audits failure when an allowlisted action script is missing", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const localPython =
      process.platform === "win32"
        ? path.join(tmpRoot, ".venv", "Scripts", "python.exe")
        : path.join(tmpRoot, ".venv", "bin", "python")
    fs.mkdirSync(path.dirname(localPython), { recursive: true })
    fs.writeFileSync(localPython, "")
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot
    vi.stubEnv("CTOA_PYTHON_BIN", "")

    const result = await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: false,
      actor: { username: "famatyyk", displayName: "Famatyyk", role: "operator" },
    })

    expect(result.ok).toBe(false)
    expect(result.output).toContain("Control Center action script not found")
    expect(result.output).not.toContain(tmpRoot)

    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.authorized).toBe(true)
    expect(audit.ok).toBe(false)
    expect(audit.output_preview).toContain("Control Center action script not found")
    expect(audit.output_preview).not.toContain(tmpRoot)
  })

  it("sanitizes successful action stdout before returning and auditing it", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    const scriptPath = path.join(tmpRoot, "scripts", "ops", "release_evidence_pack.py")
    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    fs.mkdirSync(path.dirname(scriptPath), { recursive: true })
    fs.writeFileSync(
      scriptPath,
      [
        "console.log('Completed token=secret-token-value password=legacy-password-value')",
        "console.log('Live client C:\\\\Users\\\\zycie\\\\AppData\\\\Local\\\\Solteria\\\\client')",
      ].join("\n"),
    )
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot
    process.env.CTOA_PYTHON_BIN = process.execPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_REPO_ROOT = "C:\\repo\\CTOAi"

    const result = await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: false,
      actor: { username: "famatyyk", displayName: "Famatyyk", role: "operator" },
    })

    expect(result.ok).toBe(true)
    expect(result.output).toContain("token=[redacted]")
    expect(result.output).toContain("password=[redacted]")
    expect(result.output).toContain("[external]/client")
    expect(result.output).not.toContain("secret-token-value")
    expect(result.output).not.toContain("legacy-password-value")
    expect(result.output).not.toContain("C:\\Users\\zycie")

    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.ok).toBe(true)
    expect(audit.output_preview).toContain("token=[redacted]")
    expect(audit.output_preview).toContain("password=[redacted]")
    expect(audit.output_preview).toContain("[external]/client")
    expect(JSON.stringify(audit)).not.toContain("secret-token-value")
    expect(JSON.stringify(audit)).not.toContain("legacy-password-value")
    expect(JSON.stringify(audit)).not.toContain("C:\\Users\\zycie")
  })

  it("allows local refresh actions for operator role in dry-run mode", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot

    const result = await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: true,
      actor: { username: "famatyyk", displayName: "Famatyyk", role: "operator" },
    })

    expect(result.ok).toBe(true)
    expect(result.dryRun).toBe(true)
    expect(result.output).toContain("DRY RUN ONLY")

    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.authorized).toBe(true)
    expect(audit.actor_role).toBe("operator")
    expect(audit.ok).toBe(true)
  })

  it("redacts operator-provided reasons in action audit records", async () => {
    const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ctoa-actions-"))
    process.chdir(tmpRoot)
    process.env.CTOA_WORKSPACE_ROOT = tmpRoot

    await runControlCenterAction({
      actionId: "evidence-pack-refresh",
      dryRun: true,
      reason: "maintenance token=secret-token-value sk-secret-should-not-leak {\"password\":\"json-password-value\"}",
      actor: { username: "famatyyk", displayName: "Famatyyk", role: "operator" },
    })

    const auditPath = path.join(tmpRoot, "runtime", "control-center", "action-audit.jsonl")
    const auditLines = fs.readFileSync(auditPath, "utf-8").trim().split(/\r?\n/)
    const audit = JSON.parse(auditLines[0] || "{}")
    expect(audit.reason).toContain("token=[redacted]")
    expect(audit.reason).toContain('"password":"[redacted]"')
    expect(JSON.stringify(audit)).not.toContain("secret-token-value")
    expect(JSON.stringify(audit)).not.toContain("sk-secret-should-not-leak")
    expect(JSON.stringify(audit)).not.toContain("json-password-value")
  })
})
