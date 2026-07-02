import { afterEach, describe, expect, it, vi } from "vitest"
import fs from "node:fs"
import path from "node:path"
import os from "node:os"
import {
  runControlCenterAction,
} from "../controlCenterActions"
import { canRunControlCenterAction } from "../controlCenterPolicy"

const originalCwd = process.cwd()
const originalWorkspaceRoot = process.env.CTOA_WORKSPACE_ROOT

afterEach(() => {
  process.chdir(originalCwd)
  if (originalWorkspaceRoot === undefined) {
    delete process.env.CTOA_WORKSPACE_ROOT
  } else {
    process.env.CTOA_WORKSPACE_ROOT = originalWorkspaceRoot
  }
  vi.unstubAllEnvs()
})

describe("control center action permissions", () => {
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
})
