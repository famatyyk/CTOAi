import { afterEach, describe, expect, it } from "vitest"
import { mkdir, mkdtemp, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { collectControlCenterOps } from "../controlCenterOps"

const originalEnv = {
  CTOA_RELEASES_DIR: process.env.CTOA_RELEASES_DIR,
  CTOA_REPO_HYGIENE_PATH: process.env.CTOA_REPO_HYGIENE_PATH,
  CTOA_API_COST_REPORT_PATH: process.env.CTOA_API_COST_REPORT_PATH,
  CTOA_ACTION_AUDIT_PATH: process.env.CTOA_ACTION_AUDIT_PATH,
  CTOA_EVIDENCE_JSON_PATH: process.env.CTOA_EVIDENCE_JSON_PATH,
  CTOA_ENGINE_BRAIN_MANIFEST_PATH: process.env.CTOA_ENGINE_BRAIN_MANIFEST_PATH,
  CTOA_ENGINE_BRAIN_P6_READINESS_PATH: process.env.CTOA_ENGINE_BRAIN_P6_READINESS_PATH,
  CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH: process.env.CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH,
  CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH: process.env.CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH,
  CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH: process.env.CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH,
  CTOA_ENGINE_BRAIN_DOC_SYNC_PATH: process.env.CTOA_ENGINE_BRAIN_DOC_SYNC_PATH,
  CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH: process.env.CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH,
  CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH: process.env.CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH,
  CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH: process.env.CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH,
  CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH: process.env.CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH,
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
    const brainDir = path.join(root, "AI", "generated")
    const brainManifestPath = path.join(brainDir, "manifest.json")
    const brainP6ReadinessPath = path.join(brainDir, "P6_CODEX_INTEGRATION_READINESS.json")
    const brainP6PluginHandoffSmokePath = path.join(root, "runtime", "control-center", "p6-plugin-handoff-smoke.json")
    const brainPackManifestPath = path.join(brainDir, "ENGINE_BRAIN_PACK.json")
    const brainOwnershipPath = path.join(brainDir, "OWNERSHIP_MAP.md")
    const brainDocSyncPath = path.join(brainDir, "DOC_SYNC.json")
    const brainSecretPath = path.join(brainDir, "SECRET_GUARDRAIL.json")
    const brainOperatorBriefPath = path.join(brainDir, "P7_OPERATOR_BRIEF.json")
    const brainP7CockpitSmokePath = path.join(root, "runtime", "control-center", "p7-cockpit-smoke.json")
    const brainP7SafeWriteDryRunSmokePath = path.join(root, "runtime", "control-center", "p7-safe-write-dry-run-smoke.json")

    await mkdir(sprintDir, { recursive: true })
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costReportPath), { recursive: true })
    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(path.dirname(evidenceJsonPath), { recursive: true })
    await mkdir(brainDir, { recursive: true })

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
          risk_class: "safe_write",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: 'Check local snapshot token=legacy-secret-value {"password":"json-password-value"}',
          output_preview: "dry-run output sk-secret-should-not-leak password=legacy-password-value api_key='quoted-api-key-value'",
        }),
        JSON.stringify({
          at: "2026-06-30T10:01:00.000Z",
          audit_id: "audit-2",
          actor: "zycie",
          actor_role: "owner",
          action: "evidence-pack-refresh",
          target: "local",
          risk_class: "safe_write",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Check local snapshot",
          output_preview: "dry-run output",
        }),
        JSON.stringify({
          at: "2026-06-30T10:02:00.000Z",
          audit_id: "audit-3",
          actor: "zycie",
          actor_role: "owner",
          action: "api-cost-refresh",
          target: "local",
          risk_class: "safe_write",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Refresh api cost token=legacy-secret-value",
          output_preview: "dry-run output",
        }),
        JSON.stringify({
          at: "2026-06-30T10:03:00.000Z",
          audit_id: "audit-4",
          actor: "zycie",
          actor_role: "owner",
          action: "engine-brain-refresh",
          target: "local",
          risk_class: "safe_write",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Refresh brain token=legacy-secret-value",
          output_preview: "dry-run output",
        }),
        JSON.stringify({
          at: "2026-06-30T10:04:00.000Z",
          audit_id: "audit-5",
          actor: "zycie",
          actor_role: "owner",
          action: "p7-cockpit-smoke-refresh",
          target: "local",
          risk_class: "safe_write",
          minimum_role: "operator",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "Refresh P7 cockpit smoke token=legacy-secret-value",
          output_preview: "dry-run output",
        }),
      ].join("\n"),
      "utf-8",
    )
    await writeFile(evidenceJsonPath, JSON.stringify({ generated_at: "2026-06-30T10:00:00.000Z" }), "utf-8")
    await writeFile(
      brainManifestPath,
      JSON.stringify({
        generated_at: "2026-06-30T10:02:00.000Z",
        file_count: 1100,
        doc_sync_status: "passed",
        secret_guardrail_status: "passed",
        p6_readiness_status: "ready_for_plugin_design",
        p7_operator_brief_status: "ready",
      }),
      "utf-8",
    )
    await writeFile(
      brainP6ReadinessPath,
      JSON.stringify({
        status: "ready_for_plugin_design",
        policy: "P6 plugin handoff fixture.",
        recommended_next: "Open a fresh Codex thread and verify the plugin tools.",
        checks: [
          { name: "ctoai_plugin_marketplace_entry", status: "passed", evidence: "personal marketplace entry" },
          {
            name: "ctoai_plugin_installed_cache",
            status: "passed",
            evidence: "installed personal cache version 0.1.0+codex.test",
          },
          {
            name: "ctoai_plugin_control_center_cockpit_mcp_contract",
            status: "passed",
            evidence: "home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py",
          },
        ],
      }),
      "utf-8",
    )
    await writeFile(
      brainP6PluginHandoffSmokePath,
      JSON.stringify({
        generated_at: "2026-06-30T10:02:30.000Z",
        status: "ready",
        hard_blockers: [],
        summary: {
          checks: 12,
          passed: 12,
          blocked: 0,
          current_thread_tool_discovery_status: "requires_fresh_thread",
          fresh_thread_required: true,
        },
        fresh_thread_verification: {
          status: "pending_fresh_thread",
          recommended_tool_order: [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
          ],
          next_action: "Open a fresh Codex thread and verify plugin tools.",
        },
      }),
      "utf-8",
    )
    await writeFile(brainPackManifestPath, JSON.stringify({ profile: "all", included_count: 30, truncated_count: 3 }), "utf-8")
    await writeFile(brainOwnershipPath, "# ownership\n", "utf-8")
    await writeFile(brainDocSyncPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(brainSecretPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(
      brainOperatorBriefPath,
      JSON.stringify({
        generated_at: "2026-06-30T10:02:00.000Z",
        decision: "ready_for_p7_operator_workflow",
        status: "ready",
        hard_blockers: [],
        warnings: ["diff_check"],
        next_safe_command:
          "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
        action_readiness: {
          status: "safe_write_tools_enabled",
          decision: "monitor_enabled_safe_write_tools",
          candidate_count: 5,
          audited_candidate_count: 5,
          mcp_write_tool_count: 5,
          enabled_safe_write_tools: [
            { action_id: "repo-hygiene-refresh", mcp_tool: "ctoai_repo_hygiene_refresh", risk_class: "safe_write" },
            { action_id: "api-cost-refresh", mcp_tool: "ctoai_api_cost_refresh", risk_class: "safe_write" },
            { action_id: "evidence-pack-refresh", mcp_tool: "ctoai_evidence_pack_refresh", risk_class: "safe_write" },
            { action_id: "engine-brain-refresh", mcp_tool: "ctoai_engine_brain_refresh", risk_class: "safe_write" },
            { action_id: "p7-cockpit-smoke-refresh", mcp_tool: "ctoai_p7_cockpit_smoke_refresh", risk_class: "safe_write" },
          ],
          next_safe_command:
            "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
        },
        safe_write_tool_design: {
          status: "implemented",
          decision: "ready_for_dry_run_operation",
          selected_action_id: "evidence-pack-refresh",
          proposed_mcp_tool: "ctoai_evidence_pack_refresh",
          risk_class: "safe_write",
          mode: "dry_run_first",
          mcp_enabled: true,
          next_safe_command: "Run ctoai_evidence_pack_refresh with dry_run=true.",
        },
      }),
      "utf-8",
    )
    await writeFile(
      brainP7CockpitSmokePath,
      JSON.stringify({
        generated_at: "2026-06-30T10:03:00.000Z",
        status: "ready",
        hard_blockers: [],
        warnings: [],
        summary: {
          checks: 14,
          passed: 14,
          blocked: 0,
          enabled_safe_write_tool_count: 5,
          ready_safe_write_audit_count: 5,
          expected_safe_write_audit_count: 5,
          action_audit_line_count: 5,
        },
      }),
      "utf-8",
    )
    await writeFile(
      brainP7SafeWriteDryRunSmokePath,
      JSON.stringify({
        generated_at: "2026-06-30T10:04:00.000Z",
        status: "ready",
        hard_blockers: [],
        warnings: [],
        summary: {
          checks: 12,
          passed: 12,
          blocked: 0,
          safe_write_tool_count: 5,
          dry_run_ready_count: 5,
          preflight_ready_count: 5,
          bootstrap_allowed_count: 0,
        },
      }),
      "utf-8",
    )

    process.env.CTOA_RELEASES_DIR = releasesDir
    process.env.CTOA_REPO_HYGIENE_PATH = qualityPath
    process.env.CTOA_API_COST_REPORT_PATH = costReportPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_EVIDENCE_JSON_PATH = evidenceJsonPath
    process.env.CTOA_ENGINE_BRAIN_MANIFEST_PATH = brainManifestPath
    process.env.CTOA_ENGINE_BRAIN_P6_READINESS_PATH = brainP6ReadinessPath
    process.env.CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH = brainP6PluginHandoffSmokePath
    process.env.CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH = brainPackManifestPath
    process.env.CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH = brainOwnershipPath
    process.env.CTOA_ENGINE_BRAIN_DOC_SYNC_PATH = brainDocSyncPath
    process.env.CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH = brainSecretPath
    process.env.CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH = brainOperatorBriefPath
    process.env.CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH = brainP7CockpitSmokePath
    process.env.CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH = brainP7SafeWriteDryRunSmokePath

    const ops = await collectControlCenterOps()

    expect(ops.source.mode).toBe("local")
    expect(ops.tiles.map((tile) => tile.id)).toEqual([
      "repo-hygiene",
      "release-evidence",
      "api-cost",
      "control-center-audit",
      "engine-brain",
      "operator-next",
    ])
    expect(ops.tiles[0]?.status).toBe("online")
    expect(ops.tiles[1]?.status).toBe("online")
    expect(ops.tiles[2]?.status).toBe("online")
    expect(ops.tiles[3]?.status).toBe("online")
    expect(ops.tiles[4]?.status).toBe("online")
    expect(ops.tiles[4]?.headline).toBe("ready_for_p7_operator_workflow")
    expect(ops.tiles[4]?.detail).toContain("5 enabled safe-write MCP tools")
    expect(ops.tiles[4]?.detail).toContain("P6 smoke ready 12/12")
    expect(ops.tiles[4]?.detail).toContain("smoke ready 14/14")
    expect(ops.tiles[4]?.detail).toContain("dry-run ready 5/5")
    expect(ops.tiles[4]?.detail).toContain("preflight 5/5")
    expect(ops.tiles[4]?.detail).toContain("bootstrap 0")
    expect(ops.tiles[5]?.status).toBe("online")
    expect(ops.tiles[5]?.headline).toBe("Dry-run audited P7 safe-write refreshes")
    expect(ops.tiles[5]?.detail).toContain("p7-safe-write")
    expect(ops.tiles[5]?.detail).toContain("safe_write")
    expect(ops.details.repoHygiene.sourcePath).toBe("[external]/local-pr-quality.json")
    expect(ops.details.releaseEvidenceDrilldown.status).toBe("ready")
    expect(ops.details.releaseEvidenceDrilldown.fileCount).toBe(1)
    expect(ops.details.releaseEvidenceDrilldown.sprintCount).toBe(1)
    expect(ops.details.releaseEvidenceDrilldown.recentFiles[0]?.title).toBe("Sprint 101")
    expect(ops.details.releaseComparison.currentJsonPath).toBe("[external]/latest.json")
    expect(ops.details.actionAuditDrilldown.status).toBe("ready")
    expect(ops.details.engineBrain.p7OperatorBriefStatus).toBe("ready")
    expect(ops.details.engineBrain.p6PluginHandoff.smokeStatus).toBe("ready")
    expect(ops.details.engineBrain.p6PluginHandoff.smokePassedCount).toBe(12)
    expect(ops.details.engineBrain.p6PluginHandoff.currentThreadToolDiscoveryStatus).toBe("requires_fresh_thread")
    expect(ops.details.engineBrain.p7Decision).toBe("ready_for_p7_operator_workflow")
    expect(ops.details.engineBrain.p7ActionReadinessStatus).toBe("safe_write_tools_enabled")
    expect(ops.details.engineBrain.p7ActionReadinessDecision).toBe("monitor_enabled_safe_write_tools")
    expect(ops.details.engineBrain.p7ActionAuditedCandidateCount).toBe(5)
    expect(ops.details.engineBrain.p7McpWriteToolCount).toBe(5)
    expect(ops.details.engineBrain.p7EnabledSafeWriteToolCount).toBe(5)
    expect(ops.details.engineBrain.p7ReadySafeWriteAuditCount).toBe(5)
    expect(ops.details.engineBrain.p7SafeWriteAuditCount).toBe(5)
    expect(ops.details.engineBrain.p7OperatorCockpitSummary).toBe("5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.")
    expect(ops.details.engineBrain.p7EnabledSafeWriteTools.map((tool) => tool.mcpTool)).toEqual([
      "ctoai_repo_hygiene_refresh",
      "ctoai_api_cost_refresh",
      "ctoai_evidence_pack_refresh",
      "ctoai_engine_brain_refresh",
      "ctoai_p7_cockpit_smoke_refresh",
    ])
    expect(ops.details.engineBrain.p7SafeWriteToolDesignStatus).toBe("implemented")
    expect(ops.details.engineBrain.p7SafeWriteToolProposedMcpTool).toBe("ctoai_evidence_pack_refresh")
    expect(ops.details.engineBrain.p7SafeWriteToolMcpEnabled).toBe(true)
    expect(ops.details.engineBrain.p7SafeWriteAudit).toMatchObject({
      status: "ready",
      expectedAction: "evidence-pack-refresh",
      auditId: "audit-2",
      riskClass: "safe_write",
      dryRun: true,
      authorized: "yes",
      ok: "yes",
    })
    expect(ops.details.engineBrain.p7SafeWriteAudits).toHaveLength(5)
    expect(ops.details.engineBrain.p7SafeWriteAudits.map((audit) => audit.expectedAction)).toEqual([
      "repo-hygiene-refresh",
      "api-cost-refresh",
      "evidence-pack-refresh",
      "engine-brain-refresh",
      "p7-cockpit-smoke-refresh",
    ])
    expect(ops.details.engineBrain.p7SafeWriteAudits.every((audit) => audit.status === "ready")).toBe(true)
    expect(ops.details.engineBrain.p7CockpitSmoke).toMatchObject({
      status: "ready",
      checkCount: 14,
      passedCount: 14,
      readySafeWriteAuditCount: 5,
      expectedSafeWriteAuditCount: 5,
    })
    expect(ops.details.engineBrain.p7SafeWriteDryRunSmoke).toMatchObject({
      status: "ready",
      checkCount: 12,
      passedCount: 12,
      safeWriteToolCount: 5,
      dryRunReadyCount: 5,
      preflightReadyCount: 5,
      bootstrapAllowedCount: 0,
    })
    expect(ops.details.engineBrain.sourcePaths.operatorBrief).toBe("[external]/P7_OPERATOR_BRIEF.json")
    expect(ops.details.engineBrain.sourcePaths.p6PluginHandoffSmoke).toBe("[external]/p6-plugin-handoff-smoke.json")
    expect(ops.details.engineBrain.sourcePaths.p7CockpitSmoke).toBe("[external]/p7-cockpit-smoke.json")
    expect(ops.details.engineBrain.sourcePaths.p7SafeWriteDryRunSmoke).toBe("[external]/p7-safe-write-dry-run-smoke.json")
    expect(ops.details.operatorNext).toMatchObject({
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: "Dry-run audited P7 safe-write refreshes",
      sourcePath: "[external]/P7_OPERATOR_BRIEF.json",
    })
    expect(ops.details.operatorNext.command).toContain("ctoai_evidence_pack_refresh")
    expect(ops.details.operatorNext.command).toContain("ctoai_engine_brain_refresh")
    expect(ops.details.operatorNext.command).toContain("ctoai_p7_cockpit_smoke_refresh")
    expect(ops.details.operatorNext.command).not.toMatch(/PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i)
    expect(ops.details.actionAuditDrilldown.recordCount).toBe(5)
    expect(ops.details.actionAuditDrilldown.riskCounts.safe_write).toBe(5)
    expect(ops.details.controlCenterAudit.recentActions).toHaveLength(5)
    expect(ops.details.controlCenterAudit.recentActions[1]?.action).toBe("evidence-pack-refresh")
    expect(ops.details.controlCenterAudit.recentActions[2]?.action).toBe("api-cost-refresh")
    expect(ops.details.controlCenterAudit.recentActions[3]?.action).toBe("engine-brain-refresh")
    expect(ops.details.controlCenterAudit.recentActions[4]?.action).toBe("p7-cockpit-smoke-refresh")
    expect(ops.details.controlCenterAudit.recentActions[0]?.reason).toContain("token=[redacted]")
    expect(ops.details.controlCenterAudit.recentActions[0]?.reason).toContain('"password":"[redacted]"')
    expect(ops.details.controlCenterAudit.recentActions[0]?.outputPreview).toContain("password=[redacted]")
    expect(ops.details.controlCenterAudit.recentActions[0]?.outputPreview).toContain("api_key='[redacted]'")
    expect(JSON.stringify(ops.details.actionAuditDrilldown)).not.toContain("sk-secret")
    expect(JSON.stringify(ops.details.controlCenterAudit.recentActions)).not.toContain("sk-secret")
    expect(JSON.stringify(ops.details)).not.toContain("legacy-secret-value")
    expect(JSON.stringify(ops.details)).not.toContain("legacy-password-value")
    expect(JSON.stringify(ops.details)).not.toContain("json-password-value")
    expect(JSON.stringify(ops.details)).not.toContain("quoted-api-key-value")
    expect(JSON.stringify(ops)).not.toContain(root.replace(/\\/g, "/"))
    expect(JSON.stringify(ops)).not.toContain(root)
  })

  it("does not read recent ops actions through a symlinked action audit path", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-ops-audit-symlink-"))
    const releasesDir = path.join(root, "releases", "evidence")
    const qualityPath = path.join(root, "runtime", "repo-hygiene", "local-pr-quality.json")
    const costReportPath = path.join(root, "runtime", "api-cost", "latest.json")
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    const evidenceJsonPath = path.join(root, "runtime", "evidence", "latest.json")
    const outsidePath = path.join(root, "outside-action-audit.jsonl")
    const brainDir = path.join(root, "AI", "generated")

    await mkdir(releasesDir, { recursive: true })
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costReportPath), { recursive: true })
    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(path.dirname(evidenceJsonPath), { recursive: true })
    await mkdir(brainDir, { recursive: true })
    await writeFile(
      outsidePath,
      JSON.stringify({
        at: "2026-07-06T09:20:00.000Z",
        action: "linked-ops-action",
        reason: "token=ops-secret-token-value",
      }) + "\n",
      "utf-8",
    )

    try {
      await symlink(outsidePath, auditPath)
    } catch {
      return
    }

    process.env.CTOA_RELEASES_DIR = releasesDir
    process.env.CTOA_REPO_HYGIENE_PATH = qualityPath
    process.env.CTOA_API_COST_REPORT_PATH = costReportPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_EVIDENCE_JSON_PATH = evidenceJsonPath
    process.env.CTOA_ENGINE_BRAIN_MANIFEST_PATH = path.join(brainDir, "manifest.json")
    process.env.CTOA_ENGINE_BRAIN_P6_READINESS_PATH = path.join(brainDir, "P6_CODEX_INTEGRATION_READINESS.json")
    process.env.CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH = path.join(brainDir, "ENGINE_BRAIN_PACK.json")
    process.env.CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH = path.join(brainDir, "OWNERSHIP_MAP.md")
    process.env.CTOA_ENGINE_BRAIN_DOC_SYNC_PATH = path.join(brainDir, "DOC_SYNC.json")
    process.env.CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH = path.join(brainDir, "SECRET_GUARDRAIL.json")
    process.env.CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH = path.join(brainDir, "P7_OPERATOR_BRIEF.json")

    const ops = await collectControlCenterOps()
    const serialized = JSON.stringify(ops)

    expect(ops.details.actionAuditDrilldown.status).toBe("missing")
    expect(ops.details.controlCenterAudit.recordCount).toBe(0)
    expect(ops.details.controlCenterAudit.recentActions).toEqual([])
    expect(serialized).not.toContain("linked-ops-action")
    expect(serialized).not.toContain("ops-secret-token-value")
    expect(serialized).not.toContain("outside-action-audit.jsonl")
  })
})
