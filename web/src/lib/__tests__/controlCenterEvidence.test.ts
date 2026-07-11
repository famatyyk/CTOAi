import { afterEach, describe, expect, it } from "vitest"
import crypto from "node:crypto"
import { mkdir, mkdtemp, readFile, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { collectControlCenterEvidence } from "../controlCenterEvidence"
import { getControlCenterEvidenceConfig } from "../controlCenterEvidenceConfig"

const originalEnv = {
  CTOA_RELEASES_DIR: process.env.CTOA_RELEASES_DIR,
  CTOA_REPO_HYGIENE_PATH: process.env.CTOA_REPO_HYGIENE_PATH,
  CTOA_API_COST_REPORT_PATH: process.env.CTOA_API_COST_REPORT_PATH,
  CTOA_ACTION_AUDIT_PATH: process.env.CTOA_ACTION_AUDIT_PATH,
  CTOA_HELPER_DEV_DIR: process.env.CTOA_HELPER_DEV_DIR,
  CTOA_HELPER_MANIFEST_PATH: process.env.CTOA_HELPER_MANIFEST_PATH,
  CTOA_HELPER_VALIDATION_PATH: process.env.CTOA_HELPER_VALIDATION_PATH,
  CTOA_HELPER_RELEASE_READINESS_PATH: process.env.CTOA_HELPER_RELEASE_READINESS_PATH,
  CTOA_HELPER_RELEASE_GATE_PATH: process.env.CTOA_HELPER_RELEASE_GATE_PATH,
  CTOA_HELPER_GOAL_STATUS_PATH: process.env.CTOA_HELPER_GOAL_STATUS_PATH,
  CTOA_HELPER_SMOKE_PREFLIGHT_PATH: process.env.CTOA_HELPER_SMOKE_PREFLIGHT_PATH,
  CTOA_HELPER_SMOKE_STATUS_PATH: process.env.CTOA_HELPER_SMOKE_STATUS_PATH,
  CTOA_HELPER_LIVE_PROMOTION_PATH: process.env.CTOA_HELPER_LIVE_PROMOTION_PATH,
  CTOA_HELPER_BACKGROUND_STATUS_PATH: process.env.CTOA_HELPER_BACKGROUND_STATUS_PATH,
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
  CTOA_EVIDENCE_JSON_PATH: process.env.CTOA_EVIDENCE_JSON_PATH,
  CTOA_EVIDENCE_MD_PATH: process.env.CTOA_EVIDENCE_MD_PATH,
  CTOA_API_COST_MD_OUT: process.env.CTOA_API_COST_MD_OUT,
  CTOA_API_COST_MD_PATH: process.env.CTOA_API_COST_MD_PATH,
  CTOA_EVAL_DATASET_PATH: process.env.CTOA_EVAL_DATASET_PATH,
  CTOA_PROMPT_VARIANTS_DIR: process.env.CTOA_PROMPT_VARIANTS_DIR,
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

function isolateEvidenceEnv(root: string) {
  process.env.CTOA_RELEASES_DIR = path.join(root, "releases", "evidence")
  process.env.CTOA_REPO_HYGIENE_PATH = path.join(root, "runtime", "repo-hygiene", "local-pr-quality.json")
  process.env.CTOA_API_COST_REPORT_PATH = path.join(root, "runtime", "api-cost", "latest.json")
  process.env.CTOA_API_COST_MD_OUT = path.join(root, "runtime", "api-cost", "latest.md")
  process.env.CTOA_ACTION_AUDIT_PATH = path.join(root, "runtime", "control-center", "action-audit.jsonl")
  process.env.CTOA_EVIDENCE_JSON_PATH = path.join(root, "runtime", "evidence", "latest.json")
  process.env.CTOA_EVIDENCE_MD_PATH = path.join(root, "runtime", "evidence", "latest.md")
  process.env.CTOA_HELPER_DEV_DIR = path.join(root, "runtime", "solteria_helper_dev")
  process.env.CTOA_HELPER_MANIFEST_PATH = path.join(root, "runtime", "solteria_helper_dev", "manifest.json")
  process.env.CTOA_HELPER_VALIDATION_PATH = path.join(root, "runtime", "solteria_helper_dev", "validation.json")
  process.env.CTOA_HELPER_RELEASE_READINESS_PATH = path.join(root, "runtime", "solteria_helper_dev", "release_readiness.json")
  process.env.CTOA_HELPER_RELEASE_GATE_PATH = path.join(root, "runtime", "solteria_helper_dev", "release_gate.json")
  process.env.CTOA_HELPER_GOAL_STATUS_PATH = path.join(root, "runtime", "solteria_helper_dev", "goal_status.json")
  process.env.CTOA_HELPER_SMOKE_PREFLIGHT_PATH = path.join(root, "runtime", "solteria_helper_dev", "smoke_preflight.json")
  process.env.CTOA_HELPER_SMOKE_STATUS_PATH = path.join(root, "runtime", "solteria_helper_dev", "smoke_status.json")
  process.env.CTOA_HELPER_LIVE_PROMOTION_PATH = path.join(root, "runtime", "solteria_helper_dev", "live_promotion.json")
  process.env.CTOA_HELPER_BACKGROUND_STATUS_PATH = path.join(root, "runtime", "solteria_helper_dev", "background_status.json")
  process.env.CTOA_ENGINE_BRAIN_MANIFEST_PATH = path.join(root, "AI", "generated", "manifest.json")
  process.env.CTOA_ENGINE_BRAIN_P6_READINESS_PATH = path.join(root, "AI", "generated", "P6_CODEX_INTEGRATION_READINESS.json")
  process.env.CTOA_ENGINE_BRAIN_P6_PLUGIN_HANDOFF_SMOKE_PATH = path.join(root, "runtime", "control-center", "p6-plugin-handoff-smoke.json")
  process.env.CTOA_ENGINE_BRAIN_PACK_MANIFEST_PATH = path.join(root, "AI", "generated", "ENGINE_BRAIN_PACK.json")
  process.env.CTOA_ENGINE_BRAIN_OWNERSHIP_MAP_PATH = path.join(root, "AI", "generated", "OWNERSHIP_MAP.md")
  process.env.CTOA_ENGINE_BRAIN_DOC_SYNC_PATH = path.join(root, "AI", "generated", "DOC_SYNC.json")
  process.env.CTOA_ENGINE_BRAIN_SECRET_GUARDRAIL_PATH = path.join(root, "AI", "generated", "SECRET_GUARDRAIL.json")
  process.env.CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH = path.join(root, "AI", "generated", "P7_OPERATOR_BRIEF.json")
  process.env.CTOA_ENGINE_BRAIN_P7_COCKPIT_SMOKE_PATH = path.join(root, "runtime", "control-center", "p7-cockpit-smoke.json")
  process.env.CTOA_ENGINE_BRAIN_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH = path.join(
    root,
    "runtime",
    "control-center",
    "p7-safe-write-dry-run-smoke.json",
  )
  process.env.CTOA_EVAL_DATASET_PATH = path.join(root, "evals", "dataset.jsonl")
  process.env.CTOA_PROMPT_VARIANTS_DIR = path.join(root, "evals", "prompt-variants")
}

function backgroundNoScreenPayload(generatedAt: string) {
  return {
    schema_version: "ctoa.otclient-headless-status.v1",
    status: "ready",
    mode: "background_no_screen",
    generated_at_utc: generatedAt,
    advisory_only: true,
    safe_to_run_while_playing: true,
    promotion_allowed: false,
    dispatch_allowed: false,
    runtime_actions: false,
    process_state: "running",
    interaction_contract: {
      gui_automation: false,
      mouse_keyboard_input: false,
      window_focus: false,
      screenshot_capture: false,
      client_launch: false,
      client_stop: false,
      live_file_writes: false,
      passive_reads_only: true,
      evidence_write_scope: "runtime/solteria_helper_dev",
    },
    checks: {
      no_screen_contract: true,
      client_process_stable_during_wrapper: true,
      screenshot_count_stable_during_wrapper: true,
    },
    wrapper_invariants: {
      client_process_stable: true,
      screenshot_count_stable: true,
    },
    intrusive_actions_performed: [],
    integrity: {
      status: "passed",
      matched_file_count: 58,
      manifest_file_count: 58,
      mutable_drift_count: 0,
      profile_drift_count: 0,
      mismatch_count: 0,
      missing_count: 0,
      invalid_path_count: 0,
      oversize_count: 0,
      live_files_unchanged_during_observation: true,
    },
    capability: {
      status: "fresh",
      fresh: true,
      runtime_state: "disarmed",
      runtime_actions: false,
      runtime_core_actions: false,
    },
    blockers: [],
  }
}

describe("Control Center evidence config", () => {
  it("resolves default relative evidence paths from the repository root", () => {
    for (const key of Object.keys(originalEnv)) {
      delete process.env[key]
    }

    const config = getControlCenterEvidenceConfig()
    const repoRoot = path.dirname(process.cwd())

    expect(config.releasesDir).toBe(path.join(repoRoot, "releases", "evidence"))
    expect(config.qualityPath).toBe(path.join(repoRoot, "runtime", "repo-hygiene", "local-pr-quality.json"))
    expect(config.costReportPath).toBe(path.join(repoRoot, "runtime", "api-cost", "latest.json"))
    expect(config.actionAuditPath).toBe(path.join(repoRoot, "runtime", "control-center", "action-audit.jsonl"))
    expect(config.helperDevDir).toBe(path.join(repoRoot, "runtime", "solteria_helper_dev"))
    expect(config.helperManifestPath).toBe(path.join(repoRoot, "runtime", "solteria_helper_dev", "manifest.json"))
    expect(config.helperReleaseGatePath).toBe(path.join(repoRoot, "runtime", "solteria_helper_dev", "release_gate.json"))
    expect(config.helperLivePromotionPath).toBe(path.join(repoRoot, "runtime", "solteria_helper_dev", "live_promotion.json"))
    expect(config.helperBackgroundStatusPath).toBe(path.join(repoRoot, "runtime", "solteria_helper_dev", "background_status.json"))
    expect(config.engineBrainManifestPath).toBe(path.join(repoRoot, "AI", "generated", "manifest.json"))
    expect(config.engineBrainP6ReadinessPath).toBe(path.join(repoRoot, "AI", "generated", "P6_CODEX_INTEGRATION_READINESS.json"))
    expect(config.engineBrainP6PluginHandoffSmokePath).toBe(path.join(repoRoot, "runtime", "control-center", "p6-plugin-handoff-smoke.json"))
    expect(config.engineBrainSecretGuardrailPath).toBe(path.join(repoRoot, "AI", "generated", "SECRET_GUARDRAIL.json"))
    expect(config.engineBrainOperatorBriefPath).toBe(path.join(repoRoot, "AI", "generated", "P7_OPERATOR_BRIEF.json"))
    expect(config.engineBrainP7CockpitSmokePath).toBe(path.join(repoRoot, "runtime", "control-center", "p7-cockpit-smoke.json"))
    expect(config.engineBrainP7SafeWriteDryRunSmokePath).toBe(
      path.join(repoRoot, "runtime", "control-center", "p7-safe-write-dry-run-smoke.json"),
    )
    expect(config.evidenceJsonPath).toBe(path.join(repoRoot, "runtime", "evidence", "latest.json"))
    expect(config.evidenceMarkdownPath).toBe(path.join(repoRoot, "runtime", "evidence", "latest.md"))
    expect(config.apiCostMarkdownPath).toBe(path.join(repoRoot, "runtime", "api-cost", "latest.md"))
  })

  it("uses configured paths for evidence collection", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-evidence-"))
    const releasesDir = path.join(root, "custom", "releases", "evidence")
    const sprintDir = path.join(releasesDir, "sprint-100")
    const qualityPath = path.join(root, "custom", "runtime", "repo-hygiene", "local-pr-quality.json")
    const costReportPath = path.join(root, "custom", "runtime", "api-cost", "latest.json")
    const costMarkdownPath = path.join(root, "custom", "runtime", "api-cost", "latest.md")
    const auditPath = path.join(root, "custom", "runtime", "control-center", "action-audit.jsonl")
    const evidenceJsonPath = path.join(root, "custom", "runtime", "evidence", "latest.json")
    const evidenceMarkdownPath = path.join(root, "custom", "runtime", "evidence", "latest.md")
    const helperDevDir = path.join(root, "custom", "runtime", "solteria_helper_dev")
    const helperManifestPath = path.join(helperDevDir, "manifest.json")
    const helperValidationPath = path.join(helperDevDir, "validation.json")
    const helperReadinessPath = path.join(helperDevDir, "release_readiness.json")
    const helperGatePath = path.join(helperDevDir, "release_gate.json")
    const helperGoalPath = path.join(helperDevDir, "goal_status.json")
    const helperPreflightPath = path.join(helperDevDir, "smoke_preflight.json")
    const helperSmokePath = path.join(helperDevDir, "smoke_status.json")
    const helperLivePromotionPath = path.join(helperDevDir, "live_promotion.json")
    const helperBackgroundStatusPath = path.join(helperDevDir, "background_status.json")
    const helperZipPath = path.join(helperDevDir, "ctoa_otclient_v1.1b.zip")
    const helperZipSha = crypto.createHash("sha256").update("zip-content").digest("hex")
    const brainDir = path.join(root, "custom", "AI", "generated")
    const brainManifestPath = path.join(brainDir, "manifest.json")
    const brainP6ReadinessPath = path.join(brainDir, "P6_CODEX_INTEGRATION_READINESS.json")
    const brainP6PluginHandoffSmokePath = path.join(root, "custom", "runtime", "control-center", "p6-plugin-handoff-smoke.json")
    const brainPackManifestPath = path.join(brainDir, "ENGINE_BRAIN_PACK.json")
    const brainOwnershipPath = path.join(brainDir, "OWNERSHIP_MAP.md")
    const brainDocSyncPath = path.join(brainDir, "DOC_SYNC.json")
    const brainSecretPath = path.join(brainDir, "SECRET_GUARDRAIL.json")
    const brainOperatorBriefPath = path.join(brainDir, "P7_OPERATOR_BRIEF.json")
    const brainP7CockpitSmokePath = path.join(root, "custom", "runtime", "control-center", "p7-cockpit-smoke.json")
    const brainP7SafeWriteDryRunSmokePath = path.join(
      root,
      "custom",
      "runtime",
      "control-center",
      "p7-safe-write-dry-run-smoke.json",
    )
    const datasetPath = path.join(root, "custom", "evals", "dataset.jsonl")
    const promptVariantsDir = path.join(root, "custom", "evals", "prompt-variants")

    await mkdir(sprintDir, { recursive: true })
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costReportPath), { recursive: true })
    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(path.dirname(evidenceJsonPath), { recursive: true })
    await mkdir(helperDevDir, { recursive: true })
    await mkdir(brainDir, { recursive: true })
    await mkdir(path.dirname(datasetPath), { recursive: true })
    await mkdir(promptVariantsDir, { recursive: true })

    await writeFile(path.join(sprintDir, "CTOA-100.md"), "# Evidence\n", "utf-8")
    await writeFile(
      qualityPath,
      JSON.stringify({ status: "PASS", finding_count: 0, summary: { private_count: 0, public_count: 0, review_count: 0 } }),
      "utf-8",
    )
    await writeFile(costReportPath, JSON.stringify({ records_seen: 1, total_tokens: 10, total_cost_usd: 0.1 }), "utf-8")
    await writeFile(evidenceJsonPath, JSON.stringify({ generated_at_utc: "2026-07-06T09:30:00+00:00" }), "utf-8")
    await writeFile(evidenceMarkdownPath, "# Runtime evidence\n", "utf-8")
    await writeFile(
      auditPath,
      [
        JSON.stringify({
          at: "2026-07-06T09:19:00.000Z",
          audit_id: "audit-0",
          actor_role: "owner",
          action: "repo-hygiene-refresh",
          target: "local",
          risk_class: "safe_write",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "repo hygiene dry run token=legacy-secret-value",
          output_preview: "repo hygiene dry run",
        }),
        JSON.stringify({
          at: "2026-07-06T09:20:00.000Z",
          audit_id: "audit-1",
          actor_role: "owner",
          action: "evidence-pack-refresh",
          target: "local",
          risk_class: "safe_write",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: 'test dry run token=legacy-secret-value password=legacy-password-value {"access_token":"json-token-value"}',
          output_preview: "Bearer abcdefghijklmnopqrstuvwxyz token sk-secret-should-not-leak",
        }),
        JSON.stringify({
          at: "2026-07-06T09:21:00.000Z",
          audit_id: "audit-2",
          actor_role: "owner",
          action: "api-cost-refresh",
          target: "local",
          risk_class: "safe_write",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "api dry run token=legacy-secret-value",
          output_preview: "api dry run",
        }),
        JSON.stringify({
          at: "2026-07-06T09:22:00.000Z",
          audit_id: "audit-3",
          actor_role: "owner",
          action: "engine-brain-refresh",
          target: "local",
          risk_class: "safe_write",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "brain dry run token=legacy-secret-value",
          output_preview: "brain dry run",
        }),
        JSON.stringify({
          at: "2026-07-06T09:23:00.000Z",
          audit_id: "audit-4",
          actor_role: "owner",
          action: "p7-cockpit-smoke-refresh",
          target: "local",
          risk_class: "safe_write",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: "p7 cockpit smoke dry run token=legacy-secret-value",
          output_preview: "p7 cockpit smoke dry run",
        }),
      ].join("\n") + "\n",
      "utf-8",
    )
    await writeFile(
      helperManifestPath,
      JSON.stringify({ helper_version: "v1.1b", files: [{ path: "ctoa_otclient_loader.lua", sha256: "abc" }] }),
      "utf-8",
    )
    await writeFile(helperValidationPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(helperZipPath, "zip-content", "utf-8")
    await writeFile(
      helperReadinessPath,
      JSON.stringify({ status: "static-passed", zip: { path: helperZipPath, sha256: helperZipSha } }),
      "utf-8",
    )
    await writeFile(
      helperGatePath,
      JSON.stringify({
        status: "blocked",
        releasable_to_live: false,
        next_action: "Run SmokeAttachAll after sandbox character is in-world.",
        next_command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action Launch",
        gates: [{ name: "SmokeAttachAll", status: "pending", reason: "Run SmokeAttachAll after sandbox character is in-world." }],
      }),
      "utf-8",
    )
    await writeFile(helperGoalPath, JSON.stringify({ blockers: ["SmokeAttachAll pending"] }), "utf-8")
    await writeFile(helperPreflightPath, JSON.stringify({ status: "passed", manifest: {} }), "utf-8")
    await writeFile(
      helperSmokePath,
      JSON.stringify({
        status: "ready_for_visual_review",
        next_command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action Launch",
      }),
      "utf-8",
    )
    await writeFile(
      helperBackgroundStatusPath,
      JSON.stringify(backgroundNoScreenPayload(new Date().toISOString())),
      "utf-8",
    )
    await writeFile(
      brainManifestPath,
      JSON.stringify({
        generated_at: "2026-07-06T06:23:09+00:00",
        file_count: 1056,
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
        policy: "P6 allows bounded read-only cockpit tools plus audited safe-write refreshes.",
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
          {
            name: "ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract",
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
        generated_at: "2026-07-06T06:24:30+00:00",
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
            "ctoai_engine_brain_self_check",
          ],
          next_action: "Open a fresh Codex thread and verify plugin tools.",
        },
      }),
      "utf-8",
    )
    await writeFile(
      brainPackManifestPath,
      JSON.stringify({ generated_at: "2026-07-06T06:23:24+00:00", profile: "all", included_count: 28, truncated_count: 2 }),
      "utf-8",
    )
    await writeFile(brainOwnershipPath, "# ownership\n", "utf-8")
    await writeFile(brainDocSyncPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(brainSecretPath, JSON.stringify({ status: "passed", leaks: [] }), "utf-8")
    await writeFile(
      brainOperatorBriefPath,
      JSON.stringify({
        generated_at: "2026-07-06T06:24:00+00:00",
        decision: "ready_for_p7_operator_workflow",
        status: "ready",
        hard_blockers: [],
        warnings: ["brain_doctor", "diff_check"],
        next_safe_command:
          "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
        policy: "Generated operator brief. Only audited repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke safe_write tools are allowed.",
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
        roadmap_generation: {
          status: "ready",
          doc_sync_status: "passed",
          doc_count: 4,
          ready_doc_count: 4,
          hard_blockers: [],
          next_action: "Keep roadmap generation read-only in Control Center Evidence.",
          blocked_until: "risk model coverage, audit replay evidence, Control Center gates, and tests exist before adding any new MCP write tool.",
        },
        cockpit_handoff: {
          status: "ready",
          ready: true,
          hard_blockers: [],
          warnings: [],
          p7_cockpit: {
            status: "safe_write_tools_enabled",
            enabled_safe_write_tool_count: 5,
            ready_audit_count: 5,
            audit_count: 5,
            mcp_write_tool_count: 5,
          },
          p7_cockpit_smoke: {
            status: "ready",
            checks: 14,
            passed: 14,
            blocked: 0,
            action_audit_line_count: 5,
          },
          p7_safe_write_dry_run_smoke: {
            status: "ready",
            checks: 12,
            passed: 12,
            blocked: 0,
            safe_write_tool_count: 5,
            dry_run_ready_count: 5,
            preflight_ready_count: 5,
            bootstrap_allowed_count: 0,
          },
          release_evidence: {
            status: "ready",
            file_count: 1,
            sprint_count: 1,
            latest_path: path.join(sprintDir, "CTOA-100.md"),
          },
          action_audit: {
            status: "ready",
            record_count: 5,
            latest_at: "2026-07-06T09:23:00.000Z",
            invalid_record_count: 0,
            risk_counts: { safe_write: 5 },
          },
          recommended_tool_order: [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "ctoai_evidence_pack_refresh dry_run=true",
          ],
        },
      }),
      "utf-8",
    )
    await writeFile(
      brainP7CockpitSmokePath,
      JSON.stringify({
        generated_at: "2026-07-06T06:25:00+00:00",
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
        generated_at: "2026-07-06T06:26:00+00:00",
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
        safe_write_results: [
          {
            action_id: "repo-hygiene-refresh",
            mcp_tool: "ctoai_repo_hygiene_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: true,
            preflight_bootstrap_allowed: false,
          },
          {
            action_id: "api-cost-refresh",
            mcp_tool: "ctoai_api_cost_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: true,
            preflight_bootstrap_allowed: false,
          },
          {
            action_id: "evidence-pack-refresh",
            mcp_tool: "ctoai_evidence_pack_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: true,
            preflight_bootstrap_allowed: false,
          },
          {
            action_id: "engine-brain-refresh",
            mcp_tool: "ctoai_engine_brain_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: true,
            preflight_bootstrap_allowed: false,
          },
          {
            action_id: "p7-cockpit-smoke-refresh",
            mcp_tool: "ctoai_p7_cockpit_smoke_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: true,
            preflight_bootstrap_allowed: false,
          },
        ],
      }),
      "utf-8",
    )
    await writeFile(datasetPath, '{"case_id":"case-1","category":"custom","priority":"low"}\n', "utf-8")
    await writeFile(path.join(promptVariantsDir, "baseline.md"), "# baseline\n", "utf-8")

    process.env.CTOA_RELEASES_DIR = releasesDir
    process.env.CTOA_REPO_HYGIENE_PATH = qualityPath
    process.env.CTOA_API_COST_REPORT_PATH = costReportPath
    process.env.CTOA_API_COST_MD_OUT = costMarkdownPath
    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_EVIDENCE_JSON_PATH = evidenceJsonPath
    process.env.CTOA_EVIDENCE_MD_PATH = evidenceMarkdownPath
    process.env.CTOA_HELPER_DEV_DIR = helperDevDir
    process.env.CTOA_HELPER_MANIFEST_PATH = helperManifestPath
    process.env.CTOA_HELPER_VALIDATION_PATH = helperValidationPath
    process.env.CTOA_HELPER_RELEASE_READINESS_PATH = helperReadinessPath
    process.env.CTOA_HELPER_RELEASE_GATE_PATH = helperGatePath
    process.env.CTOA_HELPER_GOAL_STATUS_PATH = helperGoalPath
    process.env.CTOA_HELPER_SMOKE_PREFLIGHT_PATH = helperPreflightPath
    process.env.CTOA_HELPER_SMOKE_STATUS_PATH = helperSmokePath
    process.env.CTOA_HELPER_LIVE_PROMOTION_PATH = helperLivePromotionPath
    process.env.CTOA_HELPER_BACKGROUND_STATUS_PATH = helperBackgroundStatusPath
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
    process.env.CTOA_EVAL_DATASET_PATH = datasetPath
    process.env.CTOA_PROMPT_VARIANTS_DIR = promptVariantsDir

    const config = getControlCenterEvidenceConfig()
    const evidence = await collectControlCenterEvidence()

    expect(config.releasesDir).toBe(releasesDir)
    expect(config.qualityPath).toBe(qualityPath)
    expect(config.costReportPath).toBe(costReportPath)
    expect(config.apiCostMarkdownPath).toBe(costMarkdownPath)
    expect(config.actionAuditPath).toBe(auditPath)
    expect(config.evidenceJsonPath).toBe(evidenceJsonPath)
    expect(config.evidenceMarkdownPath).toBe(evidenceMarkdownPath)
    expect(config.helperDevDir).toBe(helperDevDir)
    expect(config.helperReleaseGatePath).toBe(helperGatePath)
    expect(config.helperLivePromotionPath).toBe(helperLivePromotionPath)
    expect(config.helperBackgroundStatusPath).toBe(helperBackgroundStatusPath)
    expect(config.engineBrainManifestPath).toBe(brainManifestPath)
    expect(config.engineBrainP6ReadinessPath).toBe(brainP6ReadinessPath)
    expect(config.engineBrainP6PluginHandoffSmokePath).toBe(brainP6PluginHandoffSmokePath)
    expect(config.engineBrainPackManifestPath).toBe(brainPackManifestPath)
    expect(config.engineBrainOperatorBriefPath).toBe(brainOperatorBriefPath)
    expect(config.engineBrainP7CockpitSmokePath).toBe(brainP7CockpitSmokePath)
    expect(config.engineBrainP7SafeWriteDryRunSmokePath).toBe(brainP7SafeWriteDryRunSmokePath)
    expect(config.evalDatasetPath).toBe(datasetPath)
    expect(config.promptVariantsDir).toBe(promptVariantsDir)
    expect(evidence.config.costReportPath).toBe("[external]/latest.json")
    expect(evidence.config.actionAuditPath).toBe("[external]/action-audit.jsonl")
    expect(evidence.releaseEvidenceFileCount).toBe(1)
    expect(evidence.releaseEvidenceDrilldown.status).toBe("ready")
    expect(evidence.releaseEvidenceDrilldown.fileCount).toBe(1)
    expect(evidence.releaseEvidenceDrilldown.recentFiles[0].title).toBe("Evidence")
    expect(evidence.releaseEvidenceDrilldown.recentFiles[0].sprint).toBe("sprint-100")
    expect(evidence.releaseComparison.status).toBe("ready")
    expect(["runtime_newer", "same_timestamp"]).toContain(evidence.releaseComparison.relation)
    expect(evidence.releaseComparison.currentGeneratedAt).toBe("2026-07-06T09:30:00+00:00")
    expect(evidence.releaseComparison.currentJsonPath).toBe("[external]/latest.json")
    expect(evidence.releaseComparison.trackedPath).toContain("CTOA-100.md")
    expect(evidence.repoHygiene.status).toBe("PASS")
    expect(evidence.apiCostReport.status).toBe("ready")
    expect(evidence.controlCenterAudit.recordCount).toBe(5)
    expect(evidence.actionAuditDrilldown.status).toBe("ready")
    expect(evidence.actionAuditDrilldown.recordCount).toBe(5)
    expect(evidence.actionAuditDrilldown.truncated).toBe(false)
    expect(evidence.actionAuditDrilldown.sourceBytes).toBeGreaterThan(0)
    expect(evidence.actionAuditDrilldown.sampledBytes).toBe(evidence.actionAuditDrilldown.sourceBytes)
    expect(evidence.actionAuditDrilldown.dryRunCount).toBe(5)
    expect(evidence.actionAuditDrilldown.authorizedCount).toBe(5)
    expect(evidence.actionAuditDrilldown.riskCounts.safe_write).toBe(5)
    expect(evidence.actionAuditDrilldown.recentRecords.find((record) => record.action === "evidence-pack-refresh")).toMatchObject({
      action: "evidence-pack-refresh",
      riskClass: "safe_write",
      summary: 'test dry run token=[redacted] password=[redacted] {"access_token":"[redacted]"}',
    })
    expect(JSON.stringify(evidence.actionAuditDrilldown)).not.toContain("sk-secret")
    expect(JSON.stringify(evidence.actionAuditDrilldown)).not.toContain("legacy-secret-value")
    expect(JSON.stringify(evidence.actionAuditDrilldown)).not.toContain("legacy-password-value")
    expect(JSON.stringify(evidence.actionAuditDrilldown)).not.toContain("json-token-value")
    expect(evidence.otclientHelper.status).toBe("blocked")
    expect(evidence.otclientHelper.helperVersion).toBe("v1.1b")
    expect(evidence.otclientHelper.validationStatus).toBe("passed")
    expect(evidence.otclientHelper.releaseReadinessStatus).toBe("static-passed")
    expect(evidence.otclientHelper.releaseGateStatus).toBe("blocked")
    expect(evidence.otclientHelper.smokePreflightStatus).toBe("passed")
    expect(evidence.otclientHelper.smokeStatus).toBe("ready_for_visual_review")
    expect(evidence.otclientHelper.livePromotionStatus).toBe("pending")
    expect(evidence.otclientHelper.livePromoted).toBe(false)
    expect(evidence.otclientHelper.stagedFileCount).toBe(1)
    expect(evidence.otclientHelper.packageSha256).toBe(helperZipSha)
    expect(evidence.otclientHelper.nextCommand).toContain("-Action Launch")
    expect(evidence.otclientHelper.backgroundStatus).toMatchObject({
      status: "ready",
      reportedStatus: "ready",
      mode: "background_no_screen",
      maxAgeSeconds: 30,
      fresh: true,
      contractValid: true,
      contractErrors: [],
      advisoryOnly: true,
      safeToRunWhilePlaying: true,
      promotionAllowed: false,
      dispatchAllowed: false,
      runtimeActions: false,
      processState: "running",
      integrityStatus: "passed",
      matchedFileCount: 58,
      manifestFileCount: 58,
      mutableDriftCount: 0,
      capabilityStatus: "fresh",
      capabilityFresh: true,
      runtimeState: "disarmed",
      blockers: [],
    })
    expect(evidence.engineBrain.status).toBe("ready")
    expect(evidence.engineBrain.fileCount).toBe(1056)
    expect(evidence.engineBrain.docSyncStatus).toBe("passed")
    expect(evidence.engineBrain.secretGuardrailStatus).toBe("passed")
    expect(evidence.engineBrain.p6ReadinessStatus).toBe("ready_for_plugin_design")
    expect(evidence.engineBrain.p6PluginHandoff).toMatchObject({
      status: "ready",
      checkCount: 4,
      passedCheckCount: 4,
      marketplaceStatus: "passed",
      installedCacheStatus: "passed",
      installedCacheVersion: "0.1.0+codex.test",
      mcpContractCount: 2,
      passedMcpContractCount: 2,
      freshThreadRequired: true,
      smokeStatus: "ready",
      smokeCheckCount: 12,
      smokePassedCount: 12,
      smokeBlockedCount: 0,
      currentThreadToolDiscoveryStatus: "requires_fresh_thread",
      freshThreadVerificationStatus: "pending_fresh_thread",
      freshThreadRecommendedToolOrder: [
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_engine_brain_self_check",
      ],
      smokeSourcePath: "[external]/p6-plugin-handoff-smoke.json",
      sourcePath: "[external]/P6_CODEX_INTEGRATION_READINESS.json",
    })
    expect(evidence.engineBrain.p6PluginHandoff.nextAction).toContain("fresh Codex thread")
    expect(evidence.engineBrain.p6PluginHandoff.smokeNextAction).toContain("fresh Codex thread")
    expect(evidence.engineBrain.p7OperatorBriefStatus).toBe("ready")
    expect(evidence.engineBrain.p7Decision).toBe("ready_for_p7_operator_workflow")
    expect(evidence.engineBrain.p7HardBlockerCount).toBe(0)
    expect(evidence.engineBrain.p7WarningCount).toBe(2)
    expect(evidence.engineBrain.p7Warnings).toEqual(["brain_doctor", "diff_check"])
    expect(evidence.engineBrain.p7NextSafeCommand).toContain("ctoai_repo_hygiene_refresh")
    expect(evidence.engineBrain.p7RoadmapGenerationStatus).toBe("ready")
    expect(evidence.engineBrain.p7RoadmapGenerationDocSyncStatus).toBe("passed")
    expect(evidence.engineBrain.p7RoadmapGenerationReadyDocCount).toBe(4)
    expect(evidence.engineBrain.p7RoadmapGenerationDocCount).toBe(4)
    expect(evidence.engineBrain.p7RoadmapGenerationHardBlockerCount).toBe(0)
    expect(evidence.engineBrain.p7RoadmapGenerationBlockedUntil).toContain("risk model coverage")
    expect(evidence.engineBrain.p7ActionReadinessStatus).toBe("safe_write_tools_enabled")
    expect(evidence.engineBrain.p7ActionReadinessDecision).toBe("monitor_enabled_safe_write_tools")
    expect(evidence.engineBrain.p7ActionCandidateCount).toBe(5)
    expect(evidence.engineBrain.p7ActionAuditedCandidateCount).toBe(5)
    expect(evidence.engineBrain.p7McpWriteToolCount).toBe(5)
    expect(evidence.engineBrain.p7EnabledSafeWriteToolCount).toBe(5)
    expect(evidence.engineBrain.p7ReadySafeWriteAuditCount).toBe(5)
    expect(evidence.engineBrain.p7SafeWriteAuditCount).toBe(5)
    expect(evidence.engineBrain.p7OperatorCockpitSummary).toBe("5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.")
    expect(evidence.engineBrain.p7EnabledSafeWriteTools).toEqual([
      {
        actionId: "repo-hygiene-refresh",
        mcpTool: "ctoai_repo_hygiene_refresh",
        riskClass: "safe_write",
        auditStatus: "ready",
      },
      {
        actionId: "api-cost-refresh",
        mcpTool: "ctoai_api_cost_refresh",
        riskClass: "safe_write",
        auditStatus: "ready",
      },
      {
        actionId: "evidence-pack-refresh",
        mcpTool: "ctoai_evidence_pack_refresh",
        riskClass: "safe_write",
        auditStatus: "ready",
      },
      {
        actionId: "engine-brain-refresh",
        mcpTool: "ctoai_engine_brain_refresh",
        riskClass: "safe_write",
        auditStatus: "ready",
      },
      {
        actionId: "p7-cockpit-smoke-refresh",
        mcpTool: "ctoai_p7_cockpit_smoke_refresh",
        riskClass: "safe_write",
        auditStatus: "ready",
      },
    ])
    expect(evidence.engineBrain.p7ActionNextSafeCommand).toContain("ctoai_repo_hygiene_refresh")
    expect(evidence.engineBrain.p7ActionNextSafeCommand).toContain("ctoai_api_cost_refresh")
    expect(evidence.engineBrain.p7SafeWriteToolDesignStatus).toBe("implemented")
    expect(evidence.engineBrain.p7SafeWriteToolDesignDecision).toBe("ready_for_dry_run_operation")
    expect(evidence.engineBrain.p7SafeWriteToolSelectedActionId).toBe("evidence-pack-refresh")
    expect(evidence.engineBrain.p7SafeWriteToolProposedMcpTool).toBe("ctoai_evidence_pack_refresh")
    expect(evidence.engineBrain.p7SafeWriteToolMcpEnabled).toBe(true)
    expect(evidence.engineBrain.p7SafeWriteToolNextSafeCommand).toContain("ctoai_evidence_pack_refresh")
    expect(evidence.engineBrain.p7SafeWriteAudit).toMatchObject({
      status: "ready",
      expectedAction: "evidence-pack-refresh",
      proposedMcpTool: "ctoai_evidence_pack_refresh",
      auditId: "audit-1",
      riskClass: "safe_write",
      actorRole: "owner",
      authorized: "yes",
      ok: "yes",
      dryRun: true,
      summary: 'test dry run token=[redacted] password=[redacted] {"access_token":"[redacted]"}',
    })
    expect(evidence.engineBrain.p7SafeWriteAudit.nextAction).toContain("Dry-run safe-write evidence")
    expect(evidence.engineBrain.p7SafeWriteAudits).toHaveLength(5)
    expect(evidence.engineBrain.p7SafeWriteAudits.map((audit) => audit.expectedAction)).toEqual([
      "repo-hygiene-refresh",
      "api-cost-refresh",
      "evidence-pack-refresh",
      "engine-brain-refresh",
      "p7-cockpit-smoke-refresh",
    ])
    expect(evidence.engineBrain.p7SafeWriteAudits.every((audit) => audit.status === "ready")).toBe(true)
    expect(evidence.engineBrain.p7CockpitSmoke).toMatchObject({
      status: "ready",
      checkCount: 14,
      passedCount: 14,
      blockedCount: 0,
      enabledSafeWriteToolCount: 5,
      readySafeWriteAuditCount: 5,
      expectedSafeWriteAuditCount: 5,
      actionAuditLineCount: 5,
      sourcePath: "[external]/p7-cockpit-smoke.json",
    })
    expect(evidence.engineBrain.p7CockpitSmoke.nextAction).toBe("P7 cockpit smoke is ready for operator review.")
    expect(evidence.engineBrain.p7SafeWriteDryRunSmoke).toMatchObject({
      status: "ready",
      checkCount: 12,
      passedCount: 12,
      blockedCount: 0,
      safeWriteToolCount: 5,
      dryRunReadyCount: 5,
      preflightReadyCount: 5,
      bootstrapAllowedCount: 0,
      sourcePath: "[external]/p7-safe-write-dry-run-smoke.json",
    })
    expect(evidence.engineBrain.p7SafeWriteDryRunSmoke.results.every((result) => result.preflightOk)).toBe(true)
    expect(evidence.engineBrain.p7SafeWriteDryRunSmoke.results.some((result) => result.preflightBootstrapAllowed)).toBe(false)
    expect(evidence.engineBrain.p7SafeWriteDryRunSmoke.results.map((result) => result.mcpTool)).toEqual([
      "ctoai_repo_hygiene_refresh",
      "ctoai_api_cost_refresh",
      "ctoai_evidence_pack_refresh",
      "ctoai_engine_brain_refresh",
      "ctoai_p7_cockpit_smoke_refresh",
    ])
    expect(evidence.engineBrain.p7SafeWriteDryRunSmoke.nextAction).toBe("P7 safe-write dry-run smoke is ready for operator review.")
    expect(evidence.engineBrain.sourcePaths.p6PluginHandoffSmoke).toBe("[external]/p6-plugin-handoff-smoke.json")
    expect(evidence.engineBrain.sourcePaths.operatorBrief).toBe("[external]/P7_OPERATOR_BRIEF.json")
    expect(evidence.engineBrain.sourcePaths.p7CockpitSmoke).toBe("[external]/p7-cockpit-smoke.json")
    expect(evidence.engineBrain.sourcePaths.p7SafeWriteDryRunSmoke).toBe("[external]/p7-safe-write-dry-run-smoke.json")
    expect(evidence.engineBrain.packProfile).toBe("all")
    expect(evidence.engineBrain.packIncludedCount).toBe(28)
    expect(evidence.engineBrain.nextCommand).toBe(".\\ctoa.ps1 brain pack control-center")
    expect(evidence.operatorBrief).toMatchObject({
      status: "ready",
      decision: "ready_for_p7_operator_workflow",
      ready: true,
      hardBlockerCount: 0,
      warningCount: 2,
      sourcePath: "[external]/P7_OPERATOR_BRIEF.json",
      roadmapGeneration: {
        status: "ready",
        docSyncStatus: "passed",
        docCount: 4,
        readyDocCount: 4,
        hardBlockerCount: 0,
      },
      cockpitHandoff: {
        status: "ready",
        ready: true,
        hardBlockerCount: 0,
        warningCount: 0,
        p7Cockpit: {
          status: "safe_write_tools_enabled",
          enabledSafeWriteToolCount: 5,
          readyAuditCount: 5,
          auditCount: 5,
          mcpWriteToolCount: 5,
        },
        p7CockpitSmoke: {
          status: "ready",
          checks: 14,
          passed: 14,
          blocked: 0,
          actionAuditLineCount: 5,
        },
        p7SafeWriteDryRunSmoke: {
          status: "ready",
          checks: 12,
          passed: 12,
          blocked: 0,
          safeWriteToolCount: 5,
          dryRunReadyCount: 5,
          preflightReadyCount: 5,
          bootstrapAllowedCount: 0,
        },
        releaseEvidence: {
          status: "ready",
          fileCount: 1,
          sprintCount: 1,
          latestPath: "[external]/CTOA-100.md",
        },
        actionAudit: {
          status: "ready",
          recordCount: 5,
          latestAt: "2026-07-06T09:23:00.000Z",
          invalidRecordCount: 0,
          riskCounts: { safe_write: 5 },
        },
      },
    })
    expect(evidence.operatorBrief.cockpitHandoff.recommendedToolOrder).toEqual([
      "ctoai_engine_brain_brief",
      "ctoai_control_center_cockpit",
      "ctoai_evidence_pack_refresh dry_run=true",
    ])
    expect(evidence.artifactHealth.status).toBe("ready")
    expect(evidence.artifactHealth.staleCount).toBe(0)
    expect(evidence.artifactHealth.blockedCount).toBe(0)
    expect(evidence.artifactHealth.checks.map((check) => check.name)).toEqual([
      "helper_manifest_age",
      "helper_package_hash",
      "helper_smoke_evidence",
      "control_center_action_audit",
      "p7_cockpit_smoke",
      "p7_safe_write_dry_run_smoke",
    ])
    expect(evidence.artifactHealth.checks.every((check) => check.status === "passed")).toBe(true)
    expect(evidence.operatorNext).toMatchObject({
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: "Dry-run audited P7 safe-write refreshes",
      sourcePath: "[external]/P7_OPERATOR_BRIEF.json",
    })
    expect(evidence.operatorNext.command).toContain("ctoai_repo_hygiene_refresh")
    expect(evidence.operatorNext.command).toContain("ctoai_api_cost_refresh")
    expect(evidence.operatorNext.command).toContain("ctoai_evidence_pack_refresh")
    expect(evidence.operatorNext.command).toContain("ctoai_engine_brain_refresh")
    expect(evidence.operatorNext.command).not.toMatch(/PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i)
    expect(evidence.latestReleaseEvidence?.path).toContain("CTOA-100.md")

    const confirmedBrief = JSON.parse(await readFile(brainOperatorBriefPath, "utf-8"))
    confirmedBrief.next_safe_command =
      "Run ctoai_evidence_pack_refresh with dry_run=false confirm='refresh evidence pack' after reviewing runtime/control-center/action-audit.jsonl."
    confirmedBrief.action_readiness.next_safe_mode = "confirmed_selected_safe_write"
    confirmedBrief.action_readiness.next_safe_command = confirmedBrief.next_safe_command
    await writeFile(brainOperatorBriefPath, JSON.stringify(confirmedBrief), "utf-8")
    const confirmedEvidence = await collectControlCenterEvidence()
    expect(confirmedEvidence.operatorNext).toMatchObject({
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: "Confirmed P7 evidence refresh",
    })
    expect(confirmedEvidence.operatorNext.detail).toContain("exact confirmation")
    expect(confirmedEvidence.operatorNext.command).toContain("ctoai_evidence_pack_refresh")
    expect(confirmedEvidence.operatorNext.command).toContain("dry_run=false")
    expect(confirmedEvidence.operatorNext.command).toContain("refresh evidence pack")
    expect(confirmedEvidence.operatorNext.command).not.toMatch(/PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i)

    confirmedBrief.next_safe_command =
      "Review confirmed evidence-pack-refresh audit evidence in runtime/control-center/action-audit.jsonl and runtime/evidence/latest.json; design the next P7 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist."
    confirmedBrief.action_readiness.next_safe_mode = "review_confirmed_safe_write_evidence"
    confirmedBrief.action_readiness.next_safe_command = confirmedBrief.next_safe_command
    await writeFile(brainOperatorBriefPath, JSON.stringify(confirmedBrief), "utf-8")
    const reviewEvidence = await collectControlCenterEvidence()
    expect(reviewEvidence.operatorNext).toMatchObject({
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: "Review confirmed P7 evidence",
    })
    expect(reviewEvidence.operatorNext.detail).toContain("before designing the next plugin action")
    expect(reviewEvidence.operatorNext.command).toContain("Review confirmed evidence-pack-refresh audit")
    expect(reviewEvidence.operatorNext.command).toContain("runtime/evidence/latest.json")
    expect(reviewEvidence.operatorNext.command).not.toMatch(/PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i)

    confirmedBrief.next_safe_command =
      "Design the next P7 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist; keep deploy/live actions outside the plugin surface."
    confirmedBrief.action_readiness.next_safe_mode = "design_next_p7_plugin_action"
    confirmedBrief.action_readiness.next_safe_command = confirmedBrief.next_safe_command
    await writeFile(brainOperatorBriefPath, JSON.stringify(confirmedBrief), "utf-8")
    const designEvidence = await collectControlCenterEvidence()
    expect(designEvidence.operatorNext).toMatchObject({
      status: "ready",
      lane: "p7-safe-write",
      riskClass: "safe_write",
      title: "Design next P7 plugin action",
    })
    expect(designEvidence.operatorNext.detail).toContain("risk model coverage")
    expect(designEvidence.operatorNext.command).toContain("Design the next P7 plugin action")
    expect(designEvidence.operatorNext.command).not.toMatch(/PromoteLiveCtoa|ApproveLiveDeploy|live[-_\s]?deploy/i)

    await writeFile(
      brainP7SafeWriteDryRunSmokePath,
      JSON.stringify({
        generated_at: "2026-07-06T06:27:00+00:00",
        status: "ready",
        hard_blockers: [],
        warnings: [],
        summary: {
          checks: 12,
          passed: 12,
          blocked: 0,
          safe_write_tool_count: 5,
          dry_run_ready_count: 5,
          preflight_ready_count: 4,
          bootstrap_allowed_count: 1,
        },
        safe_write_results: [
          {
            action_id: "repo-hygiene-refresh",
            mcp_tool: "ctoai_repo_hygiene_refresh",
            status: "dry_run",
            audit_record_ready: true,
            preflight_ok: false,
            preflight_bootstrap_allowed: true,
          },
        ],
      }),
      "utf-8",
    )
    const bootstrapEvidence = await collectControlCenterEvidence()
    expect(bootstrapEvidence.engineBrain.p7SafeWriteDryRunSmoke).toMatchObject({
      status: "ready",
      dryRunReadyCount: 5,
      preflightReadyCount: 4,
      bootstrapAllowedCount: 1,
    })
    expect(bootstrapEvidence.engineBrain.p7SafeWriteDryRunSmoke.nextAction).toBe(
      "Rerun P7 safe-write dry-run smoke until all tools are preflight-ready with zero bootstrap.",
    )
    expect(bootstrapEvidence.artifactHealth.status).toBe("blocked")
    expect(bootstrapEvidence.artifactHealth.checks.find((check) => check.name === "p7_safe_write_dry_run_smoke")).toMatchObject({
      status: "mismatch",
      detail: "P7 safe-write dry-run smoke exists but is not ready; review runtime/control-center/p7-safe-write-dry-run-smoke.json.",
    })
    expect(bootstrapEvidence.operatorNext).toMatchObject({
      status: "blocked",
      lane: "p7-safe-write-dry-run-smoke",
      riskClass: "read_only",
      title: "Refresh P7 safe-write dry-run smoke",
    })

    expect(JSON.stringify(evidence)).not.toContain(root.replace(/\\/g, "/"))
    expect(JSON.stringify(evidence)).not.toContain(root)
    expect(JSON.stringify(confirmedEvidence)).not.toContain(root.replace(/\\/g, "/"))
    expect(JSON.stringify(confirmedEvidence)).not.toContain(root)
    expect(JSON.stringify(bootstrapEvidence)).not.toContain(root.replace(/\\/g, "/"))
    expect(JSON.stringify(bootstrapEvidence)).not.toContain(root)
  }, 15_000)

  it("fails closed for stale and invalid BackgroundNoScreen evidence", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-background-status-"))
    isolateEvidenceEnv(root)
    const helperDevDir = path.join(root, "runtime", "solteria_helper_dev")
    const backgroundStatusPath = path.join(helperDevDir, "background_status.json")
    const validPayload = backgroundNoScreenPayload(new Date(Date.now() - 31_000).toISOString())
    await mkdir(helperDevDir, { recursive: true })
    await writeFile(backgroundStatusPath, JSON.stringify(validPayload), "utf-8")

    const staleEvidence = await collectControlCenterEvidence()

    expect(staleEvidence.otclientHelper.backgroundStatus).toMatchObject({
      status: "stale",
      reportedStatus: "ready",
      fresh: false,
      contractValid: true,
      promotionAllowed: false,
      dispatchAllowed: false,
      runtimeActions: false,
    })
    expect(staleEvidence.otclientHelper.livePromoted).toBe(false)
    expect(staleEvidence.otclientHelper.releasableToLive).toBe(false)

    const untrustedPayload = structuredClone(backgroundNoScreenPayload(new Date().toISOString())) as Record<
      string,
      unknown
    >
    const untrustedIntegrity = untrustedPayload.integrity as Record<string, unknown>
    const untrustedCapability = untrustedPayload.capability as Record<string, unknown>
    untrustedPayload.status = "blocked"
    untrustedPayload.blockers = ["live_manifest_pin_untrusted"]
    untrustedIntegrity.status = "untrusted_pin"
    untrustedIntegrity.matched_file_count = 0
    untrustedIntegrity.live_files_unchanged_during_observation = false
    untrustedCapability.status = "missing"
    untrustedCapability.fresh = false
    await writeFile(backgroundStatusPath, JSON.stringify(untrustedPayload), "utf-8")

    const untrustedEvidence = await collectControlCenterEvidence()

    expect(untrustedEvidence.otclientHelper.backgroundStatus).toMatchObject({
      status: "blocked",
      reportedStatus: "blocked",
      fresh: true,
      contractValid: true,
      integrityStatus: "untrusted_pin",
      blockers: ["live_manifest_pin_untrusted"],
    })

    await writeFile(
      backgroundStatusPath,
      JSON.stringify({
        ...validPayload,
        generated_at_utc: new Date().toISOString(),
        advisory_only: false,
        promotion_allowed: true,
        blockers: "token=background-secret-value",
        integrity: { ...validPayload.integrity, matched_file_count: "not-a-number" },
      }),
      "utf-8",
    )

    const invalidEvidence = await collectControlCenterEvidence()
    const invalidBackground = invalidEvidence.otclientHelper.backgroundStatus

    expect(invalidBackground.status).toBe("blocked")
    expect(invalidBackground.contractValid).toBe(false)
    expect(invalidBackground.fresh).toBe(false)
    expect(invalidBackground.matchedFileCount).toBe(0)
    expect(invalidBackground.blockers).toEqual([])
    expect(invalidBackground.contractErrors).toEqual(
      expect.arrayContaining(["advisory_only", "promotion_allowed", "blockers", "matched_file_count"]),
    )
    expect(JSON.stringify(invalidEvidence)).not.toContain("background-secret-value")
    expect(invalidEvidence.otclientHelper.livePromoted).toBe(false)
    expect(invalidEvidence.otclientHelper.releasableToLive).toBe(false)
  })

  it("fails closed for every full BackgroundNoScreen no-action contract mutation", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-background-contract-"))
    isolateEvidenceEnv(root)
    const helperDevDir = path.join(root, "runtime", "solteria_helper_dev")
    const backgroundStatusPath = path.join(helperDevDir, "background_status.json")
    await mkdir(helperDevDir, { recursive: true })

    const mutations = [
      ["interaction_input", "interaction_contract"],
      ["interaction_numeric", "interaction_contract"],
      ["interaction_extra", "interaction_contract"],
      ["wrapper_process", "wrapper_invariants"],
      ["no_screen_check", "checks_no_screen_contract"],
      ["wrapper_process_check", "checks_client_process_stable_during_wrapper"],
      ["wrapper_screenshot_check", "checks_screenshot_count_stable_during_wrapper"],
      ["intrusive_action", "intrusive_actions_performed"],
      ["status_type", "status"],
      ["count_overflow", "integrity_count_consistency"],
      ["drift_alias", "integrity_drift_consistency"],
      ["passed_with_mismatch", "integrity_status_consistency"],
    ] as const

    for (const [mutation, expectedError] of mutations) {
      const payload = structuredClone(backgroundNoScreenPayload(new Date().toISOString())) as Record<string, unknown>
      const interaction = payload.interaction_contract as Record<string, unknown>
      const wrapper = payload.wrapper_invariants as Record<string, unknown>
      const statusChecks = payload.checks as Record<string, unknown>
      const integrity = payload.integrity as Record<string, unknown>

      if (mutation === "interaction_input") {
        interaction.mouse_keyboard_input = true
      } else if (mutation === "interaction_numeric") {
        interaction.mouse_keyboard_input = 0
      } else if (mutation === "interaction_extra") {
        interaction.unvalidated_action = false
      } else if (mutation === "wrapper_process") {
        wrapper.client_process_stable = false
      } else if (mutation === "no_screen_check") {
        statusChecks.no_screen_contract = false
      } else if (mutation === "wrapper_process_check") {
        statusChecks.client_process_stable_during_wrapper = false
      } else if (mutation === "wrapper_screenshot_check") {
        statusChecks.screenshot_count_stable_during_wrapper = false
      } else if (mutation === "intrusive_action") {
        payload.intrusive_actions_performed = ["screenshot_capture"]
      } else if (mutation === "status_type") {
        payload.status = []
      } else if (mutation === "count_overflow") {
        integrity.mismatch_count = 1
      } else if (mutation === "drift_alias") {
        integrity.profile_drift_count = 1
      } else {
        integrity.matched_file_count = 57
        integrity.mismatch_count = 1
      }

      await writeFile(backgroundStatusPath, JSON.stringify(payload), "utf-8")
      const evidence = await collectControlCenterEvidence()
      const background = evidence.otclientHelper.backgroundStatus

      expect(background.status, mutation).toBe("blocked")
      expect(background.contractValid, mutation).toBe(false)
      expect(background.fresh, mutation).toBe(false)
      expect(background.contractErrors, mutation).toContain(expectedError)
    }
  })

  it("bounds oversized action audit drilldown to a redacted tail sample", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-action-audit-tail-"))
    isolateEvidenceEnv(root)
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")

    await mkdir(path.dirname(auditPath), { recursive: true })
    await writeFile(
      auditPath,
      [
        JSON.stringify({
          at: "2026-07-06T08:00:00.000Z",
          action: "old-action",
          reason: "token=old-secret-value",
        }),
        "x".repeat(1024 * 1024 + 128),
        JSON.stringify({
          at: "2026-07-06T09:20:00.000Z",
          audit_id: "audit-tail",
          actor_role: "operator",
          action: "tail-action",
          target: "local",
          risk_class: "read_only",
          dry_run: true,
          authorized: true,
          ok: true,
          reason: 'latest tail password=tail-secret-value {"access_token":"tail-json-token"}',
        }),
      ].join("\n") + "\n",
      "utf-8",
    )

    process.env.CTOA_ACTION_AUDIT_PATH = auditPath

    const evidence = await collectControlCenterEvidence()
    const serialized = JSON.stringify(evidence.actionAuditDrilldown)

    expect(evidence.actionAuditDrilldown.status).toBe("warn")
    expect(evidence.actionAuditDrilldown.truncated).toBe(true)
    expect(evidence.actionAuditDrilldown.sourceBytes).toBeGreaterThan(evidence.actionAuditDrilldown.sampledBytes)
    expect(evidence.actionAuditDrilldown.recordCount).toBe(1)
    expect(evidence.actionAuditDrilldown.invalidRecordCount).toBe(0)
    expect(evidence.actionAuditDrilldown.actionCounts["tail-action"]).toBe(1)
    expect(evidence.actionAuditDrilldown.recentRecords[0]).toMatchObject({
      action: "tail-action",
      riskClass: "read_only",
      summary: 'latest tail password=[redacted] {"access_token":"[redacted]"}',
    })
    expect(evidence.actionAuditDrilldown.nextAction).toContain("tail-limited")
    expect(evidence.artifactHealth.checks.find((check) => check.name === "control_center_action_audit")?.status).toBe("stale")
    expect(serialized).not.toContain("old-secret-value")
    expect(serialized).not.toContain("tail-secret-value")
    expect(serialized).not.toContain("tail-json-token")
    expect(serialized).not.toContain(root.replace(/\\/g, "/"))
    expect(serialized).not.toContain(root)
  })

  it("treats symlinked configured JSON evidence as missing without reading the target", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-evidence-json-symlink-"))
    isolateEvidenceEnv(root)
    const costReportPath = path.join(root, "runtime", "api-cost", "latest.json")
    const outsidePath = path.join(root, "outside-cost.json")

    await mkdir(path.dirname(costReportPath), { recursive: true })
    await writeFile(outsidePath, JSON.stringify({ records_seen: 99, total_tokens: 12345, token: "json-secret-token-value" }), "utf-8")

    try {
      await symlink(outsidePath, costReportPath)
    } catch {
      return
    }

    const evidence = await collectControlCenterEvidence()
    const serialized = JSON.stringify(evidence)

    expect(evidence.apiCostReport.status).toBe("missing")
    expect(evidence.apiCostReport.recordsSeen).toBe(0)
    expect(evidence.recommendations).toContain(`Generate ${evidence.config.costReportPath} with scripts/ops/api_cost_report.py.`)
    expect(serialized).not.toContain("json-secret-token-value")
    expect(serialized).not.toContain("outside-cost.json")
  })

  it("fails closed when the generated P7 operator brief is symlinked", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-p7-brief-symlink-"))
    isolateEvidenceEnv(root)
    const brainDir = path.join(root, "AI", "generated")
    const brainManifestPath = path.join(brainDir, "manifest.json")
    const operatorBriefPath = path.join(brainDir, "P7_OPERATOR_BRIEF.json")
    const outsidePath = path.join(root, "outside-p7-brief.json")

    await mkdir(brainDir, { recursive: true })
    await writeFile(
      brainManifestPath,
      JSON.stringify({
        generated_at: "2026-07-06T06:23:09+00:00",
        file_count: 1056,
        doc_sync_status: "passed",
        secret_guardrail_status: "passed",
        p6_readiness_status: "ready_for_plugin_design",
        p7_operator_brief_status: "ready",
      }),
      "utf-8",
    )
    await writeFile(
      outsidePath,
      JSON.stringify({
        status: "ready",
        decision: "secret decision token=operator-secret-token",
        next_safe_command: "leak password=operator-secret-password",
      }),
      "utf-8",
    )

    try {
      await symlink(outsidePath, operatorBriefPath)
    } catch {
      return
    }

    const evidence = await collectControlCenterEvidence()
    const serialized = JSON.stringify(evidence.engineBrain)

    expect(evidence.engineBrain.status).toBe("blocked")
    expect(evidence.engineBrain.p7OperatorBriefStatus).toBe("missing")
    expect(evidence.engineBrain.p7Decision).toBe("")
    expect(evidence.engineBrain.sourcePaths.operatorBrief).toBe("[external]/P7_OPERATOR_BRIEF.json")
    expect(serialized).not.toContain("operator-secret-token")
    expect(serialized).not.toContain("operator-secret-password")
    expect(serialized).not.toContain("outside-p7-brief.json")
  })

  it("treats oversized configured JSON evidence as missing from the bounded reader", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-evidence-json-oversized-"))
    isolateEvidenceEnv(root)
    const costReportPath = path.join(root, "runtime", "api-cost", "latest.json")

    await mkdir(path.dirname(costReportPath), { recursive: true })
    await writeFile(costReportPath, `{"records_seen":99,"token":"${"x".repeat(1024 * 1024)}"}`, "utf-8")

    const evidence = await collectControlCenterEvidence()

    expect(evidence.apiCostReport.status).toBe("missing")
    expect(evidence.apiCostReport.recordsSeen).toBe(0)
  })

  it("bounds release evidence markdown title reads in drilldowns", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-release-title-oversized-"))
    isolateEvidenceEnv(root)
    const sprintDir = path.join(root, "releases", "evidence", "sprint-200")
    const evidencePath = path.join(sprintDir, "BIG-REPORT.md")

    await mkdir(sprintDir, { recursive: true })
    await writeFile(
      evidencePath,
      [`# secret-title-should-not-drive-ui`, "x".repeat(70 * 1024), "token=oversized-title-secret"].join("\n"),
      "utf-8",
    )

    const evidence = await collectControlCenterEvidence()
    const serialized = JSON.stringify(evidence.releaseEvidenceDrilldown)

    expect(evidence.releaseEvidenceDrilldown.status).toBe("ready")
    expect(evidence.releaseEvidenceDrilldown.fileCount).toBe(1)
    expect(evidence.releaseEvidenceDrilldown.recentFiles[0]).toMatchObject({
      sprint: "sprint-200",
      title: "BIG-REPORT.md",
    })
    expect(serialized).not.toContain("secret-title-should-not-drive-ui")
    expect(serialized).not.toContain("oversized-title-secret")
  })

  it("does not hash Helper package paths outside the helper dev lane", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-helper-package-escape-"))
    isolateEvidenceEnv(root)
    const helperDevDir = path.join(root, "runtime", "solteria_helper_dev")
    const helperManifestPath = path.join(helperDevDir, "manifest.json")
    const helperReadinessPath = path.join(helperDevDir, "release_readiness.json")
    const helperValidationPath = path.join(helperDevDir, "validation.json")
    const outsidePackagePath = path.join(root, "outside-package.zip")
    const outsideSha = crypto.createHash("sha256").update("outside-package-content").digest("hex")

    await mkdir(helperDevDir, { recursive: true })
    await writeFile(helperManifestPath, JSON.stringify({ helper_version: "v1.1b", files: [] }), "utf-8")
    await writeFile(helperValidationPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(outsidePackagePath, "outside-package-content", "utf-8")
    await writeFile(
      helperReadinessPath,
      JSON.stringify({ status: "static-passed", zip: { path: outsidePackagePath, sha256: outsideSha } }),
      "utf-8",
    )

    const evidence = await collectControlCenterEvidence()
    const helperPackageCheck = evidence.artifactHealth.checks.find((check) => check.name === "helper_package_hash")
    const serialized = JSON.stringify(evidence)

    expect(evidence.otclientHelper.packageSha256).toBe(outsideSha)
    expect(helperPackageCheck?.status).toBe("missing")
    expect(helperPackageCheck?.ageMinutes).toBeNull()
    expect(helperPackageCheck?.artifactPath).toBe("[external]/outside-package.zip")
    expect(evidence.artifactHealth.status).toBe("blocked")
    expect(serialized).not.toContain(outsidePackagePath)
    expect(serialized).not.toContain("outside-package-content")
  })

  it("rejects symlinked action audit evidence before tail sampling", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-action-audit-symlink-"))
    isolateEvidenceEnv(root)
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    const outsidePath = path.join(root, "outside-action-audit.jsonl")

    await mkdir(path.dirname(auditPath), { recursive: true })
    await writeFile(
      outsidePath,
      JSON.stringify({
        at: "2026-07-06T09:20:00.000Z",
        action: "linked-action",
        reason: "token=action-secret-token-value",
      }) + "\n",
      "utf-8",
    )

    try {
      await symlink(outsidePath, auditPath)
    } catch {
      return
    }

    const evidence = await collectControlCenterEvidence()
    const serialized = JSON.stringify(evidence)

    expect(evidence.actionAuditDrilldown.status).toBe("missing")
    expect(evidence.actionAuditDrilldown.recordCount).toBe(0)
    expect(evidence.controlCenterAudit.recordCount).toBe(0)
    expect(serialized).not.toContain("linked-action")
    expect(serialized).not.toContain("action-secret-token-value")
    expect(serialized).not.toContain("outside-action-audit.jsonl")
  })

  it("surfaces durable Helper live promotion evidence", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-helper-live-promotion-"))
    isolateEvidenceEnv(root)
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    const helperDevDir = path.join(root, "runtime", "solteria_helper_dev")
    const helperManifestPath = path.join(helperDevDir, "manifest.json")
    const helperValidationPath = path.join(helperDevDir, "validation.json")
    const helperReadinessPath = path.join(helperDevDir, "release_readiness.json")
    const helperGatePath = path.join(helperDevDir, "release_gate.json")
    const helperGoalPath = path.join(helperDevDir, "goal_status.json")
    const helperPreflightPath = path.join(helperDevDir, "smoke_preflight.json")
    const helperSmokePath = path.join(helperDevDir, "smoke_status.json")
    const helperLivePromotionPath = path.join(helperDevDir, "live_promotion.json")
    const helperZipPath = path.join(helperDevDir, "ctoa_otclient_v1.1b.zip")
    const helperZipSha = crypto.createHash("sha256").update("zip-content").digest("hex")

    await mkdir(path.dirname(auditPath), { recursive: true })
    await mkdir(helperDevDir, { recursive: true })
    await writeFile(auditPath, '{"action":"safe"}\n', "utf-8")
    await writeFile(
      path.join(root, "runtime", "control-center", "p7-cockpit-smoke.json"),
      JSON.stringify({
        generated_at: "2026-07-06T11:07:00+00:00",
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
          action_audit_line_count: 1,
        },
      }),
      "utf-8",
    )
    await writeFile(
      path.join(root, "runtime", "control-center", "p7-safe-write-dry-run-smoke.json"),
      JSON.stringify({
        generated_at: "2026-07-06T11:08:00+00:00",
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
    await writeFile(
      helperManifestPath,
      JSON.stringify({ helper_version: "v1.1b", created_at: "2026-07-06T09:00:00", files: [{ path: "ctoa_native_helper.lua", sha256: "abc" }] }),
      "utf-8",
    )
    await writeFile(helperValidationPath, JSON.stringify({ status: "passed" }), "utf-8")
    await writeFile(helperZipPath, "zip-content", "utf-8")
    await writeFile(
      helperReadinessPath,
      JSON.stringify({ status: "static-passed", zip: { path: helperZipPath, sha256: helperZipSha } }),
      "utf-8",
    )
    await writeFile(helperPreflightPath, JSON.stringify({ status: "passed", manifest: { created_at: "2026-07-06T09:00:00" } }), "utf-8")
    await writeFile(helperSmokePath, JSON.stringify({ status: "ready_for_visual_review" }), "utf-8")
    await writeFile(
      helperLivePromotionPath,
      JSON.stringify({
        created_at: "2026-07-06T11:06:46",
        approval_switch: "ApproveLiveDeploy",
        live_client: "C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
        backup: path.join(helperDevDir, "live_backup_20260706-110646"),
      }),
      "utf-8",
    )
    await writeFile(
      helperGatePath,
      JSON.stringify({
        status: "passed",
        releasable_to_live: true,
        next_action: "Live promotion is complete for the current staged package.",
        next_command: "",
        gates: [
          { name: "SmokeAttachAll", status: "passed", evidence: "runtime/otclient_ui_preview/smoke.json", reason: "" },
          { name: "live_approval", status: "passed", evidence: helperLivePromotionPath, reason: "" },
        ],
      }),
      "utf-8",
    )
    await writeFile(helperGoalPath, JSON.stringify({ blockers: [], next_action: "Live promotion is complete for the current staged package." }), "utf-8")

    process.env.CTOA_ACTION_AUDIT_PATH = auditPath
    process.env.CTOA_HELPER_DEV_DIR = helperDevDir
    process.env.CTOA_HELPER_MANIFEST_PATH = helperManifestPath
    process.env.CTOA_HELPER_VALIDATION_PATH = helperValidationPath
    process.env.CTOA_HELPER_RELEASE_READINESS_PATH = helperReadinessPath
    process.env.CTOA_HELPER_RELEASE_GATE_PATH = helperGatePath
    process.env.CTOA_HELPER_GOAL_STATUS_PATH = helperGoalPath
    process.env.CTOA_HELPER_SMOKE_PREFLIGHT_PATH = helperPreflightPath
    process.env.CTOA_HELPER_SMOKE_STATUS_PATH = helperSmokePath
    process.env.CTOA_HELPER_LIVE_PROMOTION_PATH = helperLivePromotionPath

    const evidence = await collectControlCenterEvidence()
    const livePromotionCheck = evidence.artifactHealth.checks.find((check) => check.name === "helper_live_promotion")

    expect(evidence.otclientHelper.status).toBe("promoted")
    expect(evidence.otclientHelper.livePromotionStatus).toBe("promoted")
    expect(evidence.otclientHelper.livePromoted).toBe(true)
    expect(evidence.otclientHelper.livePromotionCreatedAt).toBe("2026-07-06T11:06:46")
    expect(evidence.otclientHelper.liveClient).toBe("[external]/client")
    expect(evidence.otclientHelper.liveBackupPath).toContain("live_backup_20260706-110646")
    expect(evidence.otclientHelper.nextCommand).toBe("")
    expect(evidence.otclientHelper.sourcePaths.livePromotion).toBe("[external]/live_promotion.json")
    expect(livePromotionCheck?.status).toBe("passed")
    expect(evidence.artifactHealth.status).toBe("ready")
    expect(JSON.stringify(evidence)).not.toContain(root.replace(/\\/g, "/"))
    expect(JSON.stringify(evidence)).not.toContain(root)
    expect(JSON.stringify(evidence)).not.toContain("C:\\Users\\zycie")
  })
})
