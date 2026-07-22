import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ControlCenterEvidenceConfig } from "../controlCenterEvidenceConfig"

const readControlCenterJsonMock = vi.hoisted(() => vi.fn())
const readAuditLinesMock = vi.hoisted(() => vi.fn())

vi.mock("../controlCenterEvidenceIo", () => ({
  readStrictControlCenterJson: readControlCenterJsonMock,
  readBoundedControlCenterActionAuditLines: readAuditLinesMock,
  jsonHasDuplicateObjectKeys: () => false,
}))

import { collectEngineBrainStatus } from "../controlCenterEngineBrainEvidence"

const config = {
  engineBrainManifestPath: "manifest",
  engineBrainP6ReadinessPath: "p6-readiness",
  engineBrainOperatorBriefPath: "operator-brief",
  engineBrainP6PluginHandoffSmokePath: "p6-smoke",
  engineBrainP7CockpitSmokePath: "p7-smoke",
  engineBrainP7SafeWriteDryRunSmokePath: "p7-dry-run-smoke",
  actionAuditPath: "action-audit",
} as ControlCenterEvidenceConfig

describe("Engine Brain adapter uses bounded readers", () => {
  beforeEach(() => {
    readControlCenterJsonMock.mockReset()
    readAuditLinesMock.mockReset()
  })

  it("never promotes an audit actor and excludes private-user-name", async () => {
    const payloads: Record<string, Record<string, unknown>> = {
      manifest: {
        generated_at: "2026-07-21T12:00:00Z",
        doc_sync_status: "passed",
        secret_guardrail_status: "passed",
        p6_readiness_status: "ready_for_plugin_design",
      },
      "p6-readiness": {
        status: "ready_for_plugin_design",
        checks: [
          { name: "ctoai_plugin_marketplace_entry", status: "passed" },
          { name: "ctoai_plugin_installed_cache", status: "passed" },
          { name: "engine_brain_mcp_contract", status: "passed" },
        ],
      },
      "operator-brief": {
        status: "ready",
        decision: "review evidence",
        hard_blockers: [],
        warnings: [],
        action_readiness: {
          status: "ready",
          mcp_write_tool_count: 1,
          enabled_safe_write_tools: [{ action_id: "evidence-pack-refresh", mcp_tool: "ctoai_evidence_pack_refresh", risk_class: "safe_write" }],
        },
        safe_write_tool_design: { status: "ready", selected_action_id: "evidence-pack-refresh", proposed_mcp_tool: "ctoai_evidence_pack_refresh" },
      },
      "p6-smoke": { status: "ready", summary: { checks: 2, passed: 2, current_thread_tool_discovery_status: "passed" } },
      "p7-smoke": { status: "ready", summary: { checks: 2, passed: 2, blocked: 0 } },
      "p7-dry-run-smoke": {
        status: "ready",
        summary: { checks: 2, passed: 2, blocked: 0, safe_write_tool_count: 1, dry_run_ready_count: 1, preflight_ready_count: 1, bootstrap_allowed_count: 0 },
      },
    }
    readControlCenterJsonMock.mockImplementation(async (filePath: string) => payloads[filePath] || null)
    readAuditLinesMock.mockResolvedValue({
      lines: [
        JSON.stringify({
          action: "evidence-pack-refresh",
          actor: "private-user-name",
          actor_role: "operator",
          risk_class: "safe_write",
          authorized: true,
          ok: true,
          dry_run: true,
        }),
      ],
      truncated: false,
      sourceBytes: 1,
      sampledBytes: 1,
    })

    const result = await collectEngineBrainStatus(config)
    const serialized = JSON.stringify(result)

    expect(result.status).toBe("ready")
    expect(result.p7SafeWriteAudit).toMatchObject({ status: "ready", actorRole: "operator" })
    expect(serialized).not.toContain("private-user-name")
    expect(readControlCenterJsonMock).toHaveBeenCalledWith("manifest")
    expect(readAuditLinesMock).toHaveBeenCalledWith("action-audit")
  })

  it("fails closed when required evidence is unavailable", async () => {
    readControlCenterJsonMock.mockResolvedValue(null)
    readAuditLinesMock.mockResolvedValue({ lines: [], truncated: false, sourceBytes: 0, sampledBytes: 0 })

    const result = await collectEngineBrainStatus(config)

    expect(result.status).toBe("missing")
    expect(result.readOnly).toBe(true)
    expect(result.p6PluginHandoff.status).toBe("missing")
  })
})
