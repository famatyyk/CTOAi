import { afterEach, describe, expect, it } from "vitest"
import { mkdir, mkdtemp, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { collectControlCenterOps } from "../controlCenterOps"

const originalEnv = {
  CTOA_RELEASES_DIR: process.env.CTOA_RELEASES_DIR,
  CTOA_REPO_HYGIENE_PATH: process.env.CTOA_REPO_HYGIENE_PATH,
  CTOA_API_COST_REPORT_PATH: process.env.CTOA_API_COST_REPORT_PATH,
  CTOA_ACTION_AUDIT_PATH: process.env.CTOA_ACTION_AUDIT_PATH,
  CTOA_EVIDENCE_JSON_PATH: process.env.CTOA_EVIDENCE_JSON_PATH,
}

afterEach(() => {
  for (const [key, value] of Object.entries(originalEnv)) {
    if (value === undefined) {
      delete process.env[key]
    } else {
      process.env[key] = value
    }
  }
})

describe("Control Center ops", () => {
  it("collects local status tiles from runtime evidence", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-ops-"))
    const releasesDir = path.join(root, "releases", "evidence")
    const sprintDir = path.join(releasesDir, "sprint-101")
    const qualityPath = path.join(root, "runtime", "repo-hygiene", "local-pr-quality.json")
    const costReportPath = path.join(root, "runtime", "api-cost", "latest.json")
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    const evidenceJsonPath = path.join(root, "runtime", "evidence", "latest.json")

    await mkdir(sprintDir, { recursive: true })
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costReportPath), { recursive: true })
    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(path.dirname(evidenceJsonPath), { recursive: true })

    await writeFile(path.join(sprintDir, "CTOA-101.md"), "# Sprint 101\n", "utf-8")
    await writeFile(
      qualityPath,
      JSON.stringify({ status: "PASS", finding_count: 0, summary: { private_count: 1, public_count: 2, review_count: 3 } }),
      "utf-8",
    )
    await writeFile(
      costReportPath,
      JSON.stringify({ records_seen: 7, total_tokens: 321, total_cost_usd: 1.23, anomalies: [] }),
      "utf-8",
    )
    await writeFile(
      auditPath,
      [
        JSON.stringify({
          at: "2026-06-30T10:00:00.000Z",
          audit_id: "audit-1",
          actor: "zycie",
          actor_role: "owner",
          action: "repo-hygiene-refresh",
          target: "local",
          risk_class: "read_only",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Check local snapshot",
          output_preview: "dry-run output",
        }),
        JSON.stringify({
          at: "2026-06-30T10:01:00.000Z",
          audit_id: "audit-2",
          actor: "zycie",
          actor_role: "owner",
          action: "evidence-pack-refresh",
          target: "local",
          risk_class: "read_only",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Check local snapshot",
          output_preview: "dry-run output",
        }),
      ].join("\n"),
      "utf-8",
    )
    await writeFile(evidenceJsonPath, JSON.stringify({ generated_at: "2026-06-30T10:00:00.000Z" }), "utf-8")

    process.env.CTOA_RELEASES_DIR = releasesDir
    process.env.CTOA_REPO_HYGIENE_PATH = qualityPath
    process.env.CTOA_API_COST_REPORT_PATH = costReportPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_EVIDENCE_JSON_PATH = evidenceJsonPath

    const ops = await collectControlCenterOps()

    expect(ops.source.mode).toBe("local")
    expect(ops.tiles.map((tile) => tile.id)).toEqual([
      "repo-hygiene",
      "release-evidence",
      "api-cost",
      "control-center-audit",
    ])
    expect(ops.tiles[0]?.status).toBe("online")
    expect(ops.tiles[1]?.status).toBe("online")
    expect(ops.tiles[2]?.status).toBe("online")
    expect(ops.tiles[3]?.status).toBe("online")
    expect(ops.details.repoHygiene.sourcePath).toBe(qualityPath)
    expect(ops.details.controlCenterAudit.recentActions).toHaveLength(2)
    expect(ops.details.controlCenterAudit.recentActions[1]?.action).toBe("evidence-pack-refresh")
  })
})
