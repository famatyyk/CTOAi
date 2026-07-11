"use client"

import { useEffect, useState } from "react"
import type { ControlCenterEvidence } from "@/lib/controlCenterEvidence"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type EvidenceState =
  | { state: "loading"; evidence: null; error: null }
  | { state: "ready"; evidence: ControlCenterEvidence; error: null }
  | { state: "error"; evidence: null; error: string }

const statusTone: Record<string, string> = {
  PASS: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  passed: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  ready: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  ready_for_plugin_design: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  ready_for_p7_operator_workflow: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  ready_to_design_first_safe_write_tool: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  safe_write_ready: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  first_safe_write_enabled: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  safe_write_tools_enabled: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  design_ready: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  shadow_plan_ready_for_operator_review: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  implemented: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  releasable: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  promoted: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  "static-passed": "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  present: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  write_tools_blocked: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  stale: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  pending: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  missing: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  needs_attention: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  warn: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  blocked: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  operational_acceptance_blocked: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  invalid: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  FAIL: "border-pink-300/30 bg-pink-300/10 text-pink-100",
}

export default function ControlCenterEvidencePanel() {
  const [state, setState] = useState<EvidenceState>({ state: "loading", evidence: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadEvidence() {
      try {
        const response = await fetchWithTimeout("/api/control-center/evidence", { cache: "no-store" }, 5000)
        if (!response.ok) {
          throw new Error(`Evidence probe failed with HTTP ${response.status}.`)
        }
        const data = (await response.json()) as ControlCenterEvidence
        if (!cancelled) {
          setState({ state: "ready", evidence: data, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            state: "error",
            evidence: null,
            error: error instanceof Error ? error.message : "Evidence probe failed.",
          })
        }
      }
    }

    loadEvidence()
    const timer = window.setInterval(loadEvidence, 60000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const evidence = state.evidence
  const configuredCostReportPath = evidence?.config.costReportPath ?? "the configured API cost report"
  const configuredActionAuditPath = evidence?.config.actionAuditPath ?? "the configured action audit"
  const helperNextCommand =
    evidence?.otclientHelper.nextCommand ||
    (evidence?.otclientHelper.livePromoted
      ? "No command needed."
      : "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ValidateDev")
  const helperBlockers = evidence?.otclientHelper.blockers.length
    ? evidence.otclientHelper.blockers
    : evidence?.otclientHelper.livePromoted
      ? ["No helper blockers."]
      : ["No helper blockers loaded yet."]
  const releaseEvidenceFiles = evidence?.releaseEvidenceDrilldown.recentFiles.length
    ? evidence.releaseEvidenceDrilldown.recentFiles
    : placeholderReleaseEvidenceFiles()
  const actionAuditRecords = evidence?.actionAuditDrilldown.recentRecords.length
    ? evidence.actionAuditDrilldown.recentRecords
    : placeholderActionAuditRecords()
  const actionAuditSampleDetail = evidence?.actionAuditDrilldown.truncated
    ? `Tail sample ${formatBytes(evidence.actionAuditDrilldown.sampledBytes)} of ${formatBytes(evidence.actionAuditDrilldown.sourceBytes)}.`
    : evidence?.actionAuditDrilldown.latestAt
      ? `Latest ${formatTimestamp(evidence.actionAuditDrilldown.latestAt)}`
      : "No audit records found."
  const helperBackgroundStatus = evidence?.otclientHelper.backgroundStatus
  const helperBackgroundDetail = !helperBackgroundStatus
    ? "Waiting for passive background evidence."
    : !helperBackgroundStatus.contractValid
      ? `Contract blocked: ${helperBackgroundStatus.contractErrors.slice(0, 2).join(", ") || "invalid artifact"}.`
      : !helperBackgroundStatus.fresh
        ? `Snapshot stale after ${helperBackgroundStatus.maxAgeSeconds}s; collect a new passive sample.`
        : helperBackgroundStatus.status === "ready"
          ? `${helperBackgroundStatus.integrityStatus} · ${helperBackgroundStatus.runtimeState} · advisory only; promotion and dispatch disabled.`
          : helperBackgroundStatus.integrityStatus === "untrusted_pin"
            ? `${helperBackgroundStatus.pinClassification} · diagnostic ${helperBackgroundStatus.diagnosticParityStatus}${helperBackgroundStatus.diagnosticParityAttempted ? ` / profile drift ${helperBackgroundStatus.diagnosticProfileDriftCount}` : ""} · current gated official promotion required; historical rebinding forbidden.`
          : helperBackgroundStatus.blockers[0]
            ? `Blocked: ${helperBackgroundStatus.blockers[0]}.`
            : `Passive evidence: ${helperBackgroundStatus.status}.`
  const helperConditionsShadow = evidence?.otclientHelper.conditionsShadowReplay
  const helperConditionsShadowDetail = !helperConditionsShadow
    ? "Waiting for the data-only Conditions replay report."
    : !helperConditionsShadow.contractValid
      ? `Contract blocked: ${helperConditionsShadow.contractErrors.slice(0, 2).join(", ") || "invalid artifact"}.`
      : !helperConditionsShadow.fresh
        ? `Replay stale after ${helperConditionsShadow.maxAgeSeconds}s; run a new bounded replay.`
        : helperConditionsShadow.status === "shadow_plan_ready_for_operator_review"
          ? `${helperConditionsShadow.scenarioPassedCount}/${helperConditionsShadow.scenarioTotalCount} deterministic fixtures; operator review required, all actions disabled.`
          : helperConditionsShadow.blockers[0]
            ? `Blocked: ${helperConditionsShadow.blockers[0]}; fixture pack ${helperConditionsShadow.scenarioPackStatus}.`
            : `Conditions replay: ${helperConditionsShadow.status}.`

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Evidence and reporting</p>
          <p className="mt-1 text-sm text-slate-400">
            Release evidence, local quality checks, cost reporting and Control Center audit traces.
          </p>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
          {state.state === "loading" ? "loading" : evidence ? `updated ${new Date(evidence.generatedAt).toLocaleTimeString()}` : "offline"}
        </span>
      </div>

      {state.state === "error" ? (
        <div className="mt-6 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{state.error}</div>
      ) : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Latest release evidence"
          value={evidence?.latestReleaseEvidence ? "ready" : "missing"}
          detail={evidence?.latestReleaseEvidence ? evidence.latestReleaseEvidence.path : "No release evidence markdown found yet."}
          tone={statusTone[evidence?.latestReleaseEvidence ? "ready" : "missing"]}
        />
        <MetricCard
          label="Repo hygiene"
          value={evidence ? evidence.repoHygiene.status : "loading"}
          detail={
            evidence
              ? `${evidence.repoHygiene.findingCount} findings, private ${evidence.repoHygiene.summary.private_count ?? 0}, public ${evidence.repoHygiene.summary.public_count ?? 0}`
              : "Waiting for repo hygiene snapshot."
          }
          tone={statusTone[evidence?.repoHygiene.status || "missing"] || statusTone.missing}
        />
        <MetricCard
          label="API cost report"
          value={evidence ? evidence.apiCostReport.status : "loading"}
          detail={
            evidence
              ? `${evidence.apiCostReport.recordsSeen} records, ${evidence.apiCostReport.totalTokens} tokens, $${evidence.apiCostReport.totalCostUsd.toFixed(2)}`
              : `Waiting for ${configuredCostReportPath}.`
          }
          tone={statusTone[evidence?.apiCostReport.status || "missing"] || statusTone.missing}
        />
        <MetricCard
          label="Control Center audit"
          value={evidence ? evidence.controlCenterAudit.status : "loading"}
          detail={
            evidence
              ? `${evidence.controlCenterAudit.recordCount} action records`
              : `Waiting for ${configuredActionAuditPath} traces.`
          }
          tone={statusTone[evidence?.controlCenterAudit.status || "missing"] || statusTone.missing}
        />
      </div>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">P7 operator brief</p>
            <p className="mt-1 text-sm text-slate-400">
              Read-only handoff from AI/generated/P7_OPERATOR_BRIEF.json into cockpit evidence.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.operatorBrief.status || "missing"] || statusTone.missing}`}>
            {evidence?.operatorBrief.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-8">
          <MetricCard
            label="Handoff"
            value={evidence?.operatorBrief.cockpitHandoff.status || "loading"}
            detail={
              evidence
                ? `ready ${String(evidence.operatorBrief.cockpitHandoff.ready)}; blockers ${evidence.operatorBrief.cockpitHandoff.hardBlockerCount}; warnings ${evidence.operatorBrief.cockpitHandoff.warningCount}`
                : "Waiting for cockpit handoff."
            }
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P7 cockpit"
            value={
              evidence
                ? `${evidence.operatorBrief.cockpitHandoff.p7Cockpit.readyAuditCount}/${evidence.operatorBrief.cockpitHandoff.p7Cockpit.auditCount}`
                : "loading"
            }
            detail={`${evidence?.operatorBrief.cockpitHandoff.p7Cockpit.enabledSafeWriteToolCount ?? 0} safe-write tools; ${evidence?.operatorBrief.cockpitHandoff.p7Cockpit.mcpWriteToolCount ?? 0} MCP write tools`}
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.p7Cockpit.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Smoke"
            value={evidence?.operatorBrief.cockpitHandoff.p7CockpitSmoke.status || "loading"}
            detail={
              evidence
                ? `${evidence.operatorBrief.cockpitHandoff.p7CockpitSmoke.passed}/${evidence.operatorBrief.cockpitHandoff.p7CockpitSmoke.checks} checks; audit lines ${evidence.operatorBrief.cockpitHandoff.p7CockpitSmoke.actionAuditLineCount}`
                : "Waiting for smoke evidence."
            }
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.p7CockpitSmoke.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Dry-run smoke"
            value={evidence?.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.status || "loading"}
            detail={
              evidence
                ? `${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.safeWriteToolCount} tools; preflight ${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.preflightReadyCount}/${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.safeWriteToolCount}; bootstrap ${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.bootstrapAllowedCount}; ${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.passed}/${evidence.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.checks} checks`
                : "Waiting for dry-run smoke evidence."
            }
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.p7SafeWriteDryRunSmoke.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Release evidence"
            value={evidence?.operatorBrief.cockpitHandoff.releaseEvidence.status || "loading"}
            detail={`${evidence?.operatorBrief.cockpitHandoff.releaseEvidence.fileCount ?? 0} files; ${evidence?.operatorBrief.cockpitHandoff.releaseEvidence.sprintCount ?? 0} sprints`}
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.releaseEvidence.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Action audit"
            value={evidence?.operatorBrief.cockpitHandoff.actionAudit.status || "loading"}
            detail={
              evidence
                ? `${evidence.operatorBrief.cockpitHandoff.actionAudit.recordCount} records; invalid ${evidence.operatorBrief.cockpitHandoff.actionAudit.invalidRecordCount}`
                : "Waiting for action audit."
            }
            tone={statusTone[evidence?.operatorBrief.cockpitHandoff.actionAudit.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Roadmap"
            value={evidence?.operatorBrief.roadmapGeneration.status || "loading"}
            detail={
              evidence
                ? `${evidence.operatorBrief.roadmapGeneration.readyDocCount}/${evidence.operatorBrief.roadmapGeneration.docCount} docs; doc sync ${evidence.operatorBrief.roadmapGeneration.docSyncStatus}`
                : "Waiting for roadmap generation evidence."
            }
            tone={statusTone[evidence?.operatorBrief.roadmapGeneration.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Brief blockers"
            value={String(evidence?.operatorBrief.hardBlockerCount ?? 0)}
            detail={`${evidence?.operatorBrief.warningCount ?? 0} warnings; ${evidence?.operatorBrief.decision || "no decision"}`}
            tone={statusTone[evidence?.operatorBrief.status || "missing"] || statusTone.missing}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recommended tool order</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(evidence?.operatorBrief.cockpitHandoff.recommendedToolOrder.length
                ? evidence.operatorBrief.cockpitHandoff.recommendedToolOrder
                : ["ctoai_engine_brain_brief"]
              ).map((tool) => (
                <span key={tool} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
                  {tool}
                </span>
              ))}
            </div>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.operatorBrief.nextSafeCommand || "Run .\\ctoa.ps1 brain refresh to generate the operator brief."}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Source</p>
            <p className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.operatorBrief.sourcePath || "AI/generated/P7_OPERATOR_BRIEF.json"}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Latest release path</p>
            <p className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.operatorBrief.cockpitHandoff.releaseEvidence.latestPath || "No release evidence path loaded."}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">Operator next</p>
            <p className="mt-1 text-sm text-slate-400">
              One read-only recommendation selected from the current gates; guarded live actions are not exposed as a command here.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.operatorNext.status || "missing"] || statusTone.missing}`}>
            {evidence?.operatorNext.status || "loading"}
          </span>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
              {evidence?.operatorNext.lane || "operator lane"} · {evidence?.operatorNext.riskClass || "read_only"}
            </p>
            <p className="mt-3 text-base font-black text-slate-100">{evidence?.operatorNext.title || "Waiting for evidence."}</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.operatorNext.detail || "Collecting local evidence before choosing the next operator step."}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Operator command</p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.operatorNext.command || "Manual review only."}
            </p>
            <p className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-slate-500">
              {evidence?.operatorNext.sourcePath || "Waiting for source evidence."}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">OTClient Helper status</p>
            <p className="mt-1 text-sm text-slate-400">
              Read-only Solteria Helper package, validation and release gate state from runtime artifacts.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.otclientHelper.status || "missing"] || statusTone.missing}`}>
            {evidence?.otclientHelper.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-7">
          <MetricCard
            label="Helper version"
            value={evidence?.otclientHelper.helperVersion || "loading"}
            detail={evidence?.otclientHelper.packageSha256 ? `ZIP ${evidence.otclientHelper.packageSha256.slice(0, 12)}` : "Package hash not generated yet."}
            tone={statusTone[evidence?.otclientHelper.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Validation"
            value={evidence?.otclientHelper.validationStatus || "loading"}
            detail={`${evidence?.otclientHelper.stagedFileCount ?? 0} staged files`}
            tone={statusTone[evidence?.otclientHelper.validationStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Release gate"
            value={evidence?.otclientHelper.releaseGateStatus || "loading"}
            detail={
              evidence?.otclientHelper.livePromoted
                ? "Live promotion evidence is recorded."
                : evidence?.otclientHelper.releasableToLive
                  ? "Ready only after explicit live approval."
                  : "Live promotion is blocked."
            }
            tone={statusTone[evidence?.otclientHelper.releaseGateStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Live promotion"
            value={evidence?.otclientHelper.livePromotionStatus || "loading"}
            detail={
              evidence?.otclientHelper.livePromoted
                ? `Promoted ${formatTimestamp(evidence.otclientHelper.livePromotionCreatedAt)}`
                : "No accepted live promotion evidence yet."
            }
            tone={statusTone[evidence?.otclientHelper.livePromotionStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Smoke"
            value={evidence?.otclientHelper.smokePreflightStatus || "loading"}
            detail={`Sandbox status: ${evidence?.otclientHelper.smokeStatus || "missing"}`}
            tone={statusTone[evidence?.otclientHelper.smokePreflightStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="BackgroundNoScreen"
            value={helperBackgroundStatus?.status || "loading"}
            detail={helperBackgroundDetail}
            tone={statusTone[helperBackgroundStatus?.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P9 Conditions shadow"
            value={helperConditionsShadow?.status || "loading"}
            detail={helperConditionsShadowDetail}
            tone={statusTone[helperConditionsShadow?.status || "missing"] || statusTone.missing}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next safe command</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.otclientHelper.nextAction || "Waiting for helper evidence."}</p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {helperNextCommand}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Blocking gates</p>
            <div className="mt-3 space-y-2">
              {helperBlockers.slice(0, 4).map((item) => (
                <p key={item} className="text-sm leading-6 text-slate-300">{item}</p>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Live evidence</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <p className="overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.otclientHelper.liveClient || "Live client path not reported."}
            </p>
            <p className="overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.otclientHelper.liveBackupPath || "Live backup path not reported."}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">Engine Brain status</p>
            <p className="mt-1 text-sm text-slate-400">
              Read-only context freshness, doc sync and secret guardrail state from AI/generated artifacts.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.engineBrain.status || "missing"] || statusTone.missing}`}>
            {evidence?.engineBrain.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-8">
          <MetricCard
            label="Brain files"
            value={evidence ? String(evidence.engineBrain.fileCount) : "loading"}
            detail={evidence?.engineBrain.generatedAt ? `Generated ${formatTimestamp(evidence.engineBrain.generatedAt)}` : "Manifest not generated yet."}
            tone={statusTone[evidence?.engineBrain.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Doc sync"
            value={evidence?.engineBrain.docSyncStatus || "loading"}
            detail="CLI docs, command dictionary and roadmap checks."
            tone={statusTone[evidence?.engineBrain.docSyncStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Secret guardrail"
            value={evidence?.engineBrain.secretGuardrailStatus || "loading"}
            detail="Generated context exact sensitive-path scan."
            tone={statusTone[evidence?.engineBrain.secretGuardrailStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P6 readiness"
            value={evidence?.engineBrain.p6ReadinessStatus || "loading"}
            detail="Codex plugin design gate from the generated manifest."
            tone={statusTone[evidence?.engineBrain.p6ReadinessStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P6 plugin"
            value={evidence?.engineBrain.p6PluginHandoff.status || "loading"}
            detail={
              evidence
                ? `${evidence.engineBrain.p6PluginHandoff.installedCacheVersion || "no cache version"}; checks ${evidence.engineBrain.p6PluginHandoff.passedCheckCount}/${evidence.engineBrain.p6PluginHandoff.checkCount}; smoke ${evidence.engineBrain.p6PluginHandoff.smokeStatus} ${evidence.engineBrain.p6PluginHandoff.smokePassedCount}/${evidence.engineBrain.p6PluginHandoff.smokeCheckCount}`
                : "Waiting for P6 plugin handoff evidence."
            }
            tone={statusTone[evidence?.engineBrain.p6PluginHandoff.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P7 brief"
            value={evidence?.engineBrain.p7OperatorBriefStatus || "loading"}
            detail={
              evidence?.engineBrain.p7Decision
                ? `${evidence.engineBrain.p7Decision}; blockers ${evidence.engineBrain.p7HardBlockerCount}; warnings ${evidence.engineBrain.p7WarningCount}`
                : "Operator brief not generated yet."
            }
            tone={statusTone[evidence?.engineBrain.p7OperatorBriefStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="P7 action gate"
            value={evidence?.engineBrain.p7ActionReadinessStatus || "loading"}
            detail={
              evidence
                ? evidence.engineBrain.p7OperatorCockpitSummary
                : "Waiting for P7 action readiness."
            }
            tone={statusTone[evidence?.engineBrain.p7ActionReadinessStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Safe-write design"
            value={evidence?.engineBrain.p7SafeWriteToolDesignStatus || "loading"}
            detail={
              evidence?.engineBrain.p7SafeWriteToolProposedMcpTool
                ? `${evidence.engineBrain.p7SafeWriteToolProposedMcpTool}; MCP enabled ${evidence.engineBrain.p7SafeWriteToolMcpEnabled}`
                : "Waiting for safe-write tool design."
            }
            tone={statusTone[evidence?.engineBrain.p7SafeWriteToolDesignStatus || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Safe-write audit"
            value={
              evidence?.engineBrain.p7SafeWriteAuditCount
                ? `${evidence.engineBrain.p7ReadySafeWriteAuditCount}/${evidence.engineBrain.p7SafeWriteAuditCount} ready`
                : evidence?.engineBrain.p7SafeWriteAudit.status || "loading"
            }
            detail={
              evidence?.engineBrain.p7SafeWriteAudit.latestAt
                ? `${evidence.engineBrain.p7SafeWriteAudit.expectedAction}; ${evidence.engineBrain.p7SafeWriteAudit.dryRun ? "dry-run" : "confirmed"}; ok ${evidence.engineBrain.p7SafeWriteAudit.ok}`
                : evidence?.engineBrain.p7SafeWriteAudit.nextAction || "Waiting for safe-write audit evidence."
            }
            tone={
              statusTone[
                evidence?.engineBrain.p7SafeWriteAudits.length &&
                evidence.engineBrain.p7SafeWriteAudits.every((audit) => audit.status === "ready")
                  ? "ready"
                  : evidence?.engineBrain.p7SafeWriteAudit.status || "missing"
              ] || statusTone.missing
            }
          />
          <MetricCard
            label="P7 smoke"
            value={evidence?.engineBrain.p7CockpitSmoke.status || "loading"}
            detail={
              evidence
                ? `${evidence.engineBrain.p7CockpitSmoke.passedCount}/${evidence.engineBrain.p7CockpitSmoke.checkCount} checks; audits ${evidence.engineBrain.p7CockpitSmoke.readySafeWriteAuditCount}/${evidence.engineBrain.p7CockpitSmoke.expectedSafeWriteAuditCount}`
                : "Waiting for P7 cockpit smoke."
            }
            tone={statusTone[evidence?.engineBrain.p7CockpitSmoke.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Dry-run smoke"
            value={evidence?.engineBrain.p7SafeWriteDryRunSmoke.status || "loading"}
            detail={
              evidence
                ? `${evidence.engineBrain.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount} tools; preflight ${evidence.engineBrain.p7SafeWriteDryRunSmoke.preflightReadyCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount}; bootstrap ${evidence.engineBrain.p7SafeWriteDryRunSmoke.bootstrapAllowedCount}; ${evidence.engineBrain.p7SafeWriteDryRunSmoke.passedCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.checkCount} checks`
                : "Waiting for P7 dry-run smoke."
            }
            tone={statusTone[evidence?.engineBrain.p7SafeWriteDryRunSmoke.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Pack profile"
            value={evidence?.engineBrain.packProfile || "loading"}
            detail={evidence ? `${evidence.engineBrain.packIncludedCount} sections, ${evidence.engineBrain.packTruncatedCount} truncated` : "Waiting for pack manifest."}
            tone={statusTone[evidence?.engineBrain.status || "missing"] || statusTone.missing}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next context command</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.engineBrain.nextAction || "Waiting for Engine Brain evidence."}</p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.nextCommand || ".\\ctoa.ps1 brain refresh"}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">P7 operator handoff</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7Policy || "Waiting for generated P7 operator policy."}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 cockpit status</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7OperatorCockpitSummary || "Waiting for generated P7 cockpit summary."}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P6 plugin handoff</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence
                ? `${evidence.engineBrain.p6PluginHandoff.marketplaceStatus}/${evidence.engineBrain.p6PluginHandoff.installedCacheStatus}; smoke ${evidence.engineBrain.p6PluginHandoff.smokeStatus}; discovery ${evidence.engineBrain.p6PluginHandoff.currentThreadToolDiscoveryStatus}; fresh thread ${String(evidence.engineBrain.p6PluginHandoff.freshThreadRequired)}. ${evidence.engineBrain.p6PluginHandoff.nextAction}`
                : "Waiting for P6 plugin handoff evidence."}
            </p>
            {evidence?.engineBrain.p6PluginHandoff.freshThreadRecommendedToolOrder.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {evidence.engineBrain.p6PluginHandoff.freshThreadRecommendedToolOrder.map((tool) => (
                  <span key={tool} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
                    {tool}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-slate-500">
              readiness {evidence?.engineBrain.p6PluginHandoff.sourcePath || "AI/generated/P6_CODEX_INTEGRATION_READINESS.json"}; smoke{" "}
              {evidence?.engineBrain.p6PluginHandoff.smokeSourcePath || "runtime/control-center/p6-plugin-handoff-smoke.json"}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(evidence?.engineBrain.p7EnabledSafeWriteTools.length ? evidence.engineBrain.p7EnabledSafeWriteTools : []).map((tool) => (
                <span key={`${tool.actionId}-${tool.mcpTool}`} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
                  {tool.mcpTool || tool.actionId}: {tool.auditStatus}
                </span>
              ))}
            </div>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.p7NextSafeCommand || "Run .\\ctoa.ps1 brain refresh to generate the operator brief."}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 action gate</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7ActionReadinessDecision || "Waiting for P7 action readiness."}
            </p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.p7ActionNextSafeCommand || "Keep plugin MCP read-only until action evidence is ready."}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Safe-write design</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7SafeWriteToolDesignDecision
                ? `${evidence.engineBrain.p7SafeWriteToolDesignDecision}; selected ${evidence.engineBrain.p7SafeWriteToolSelectedActionId || "n/a"}; ${evidence.engineBrain.p7SafeWriteToolMode || "missing"}`
                : "Waiting for safe-write tool design."}
            </p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.p7SafeWriteToolNextSafeCommand || "Keep MCP write tools disabled until design and tests are ready."}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Safe-write audit</p>
            <div className="mt-3 grid gap-2">
              {(evidence?.engineBrain.p7SafeWriteAudits.length
                ? evidence.engineBrain.p7SafeWriteAudits
                : evidence?.engineBrain.p7SafeWriteAudit
                  ? [evidence.engineBrain.p7SafeWriteAudit]
                  : []
              ).map((audit) => (
                <div key={`${audit.expectedAction}-${audit.auditId || audit.proposedMcpTool}`} className="rounded-xl bg-black/20 p-3">
                  <p className="font-mono text-xs text-cyan-100">{audit.proposedMcpTool || audit.expectedAction}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {audit.latestAt
                      ? `${audit.expectedAction}; ${audit.riskClass}; ${audit.dryRun ? "dry-run" : "confirmed"}; authorized ${audit.authorized}; ok ${audit.ok}`
                      : audit.nextAction}
                  </p>
                  {audit.summary ? <p className="mt-2 text-sm leading-6 text-slate-400">{audit.summary}</p> : null}
                </div>
              ))}
            </div>
            {evidence?.engineBrain.p7Warnings.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {evidence.engineBrain.p7Warnings.map((warning) => (
                  <span key={warning} className="rounded-full bg-amber-300/10 px-3 py-1 text-xs font-bold text-amber-100">
                    {warning}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 cockpit smoke</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7CockpitSmoke.status
                ? `${evidence.engineBrain.p7CockpitSmoke.status}; ${evidence.engineBrain.p7CockpitSmoke.passedCount}/${evidence.engineBrain.p7CockpitSmoke.checkCount} checks; safe-write audits ${evidence.engineBrain.p7CockpitSmoke.readySafeWriteAuditCount}/${evidence.engineBrain.p7CockpitSmoke.expectedSafeWriteAuditCount}`
                : "Waiting for P7 cockpit smoke evidence."}
            </p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.p7CockpitSmoke.nextAction || ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_cockpit_smoke.py"}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 safe-write dry-run smoke</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {evidence?.engineBrain.p7SafeWriteDryRunSmoke.status
                ? `${evidence.engineBrain.p7SafeWriteDryRunSmoke.status}; ${evidence.engineBrain.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount} dry-run tools; ${evidence.engineBrain.p7SafeWriteDryRunSmoke.preflightReadyCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.safeWriteToolCount} preflight; ${evidence.engineBrain.p7SafeWriteDryRunSmoke.bootstrapAllowedCount} bootstrap; ${evidence.engineBrain.p7SafeWriteDryRunSmoke.passedCount}/${evidence.engineBrain.p7SafeWriteDryRunSmoke.checkCount} checks`
                : "Waiting for P7 safe-write dry-run smoke evidence."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(evidence?.engineBrain.p7SafeWriteDryRunSmoke.results.length ? evidence.engineBrain.p7SafeWriteDryRunSmoke.results : []).map((result) => (
                <span key={`${result.actionId}-${result.mcpTool}`} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
                  {result.mcpTool || result.actionId}: {result.auditRecordReady && result.preflightOk ? "ready" : result.auditRecordReady && result.preflightBootstrapAllowed ? "bootstrap" : result.status}
                </span>
              ))}
            </div>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.engineBrain.p7SafeWriteDryRunSmoke.nextAction || ".\\.venv\\Scripts\\python.exe scripts\\ops\\control_center_p7_safe_write_dry_run_smoke.py"}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">Artifact freshness</p>
            <p className="mt-1 text-sm text-slate-400">
              Read-only stale-artifact checks for manifest age, package hash, smoke evidence, and action audit traces.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.artifactHealth.status || "missing"] || statusTone.missing}`}>
            {evidence?.artifactHealth.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {(evidence?.artifactHealth.checks.length ? evidence.artifactHealth.checks : placeholderArtifactChecks()).map((check) => (
            <MetricCard
              key={check.name}
              label={formatCheckName(check.name)}
              value={check.status}
              detail={`${check.detail}${check.ageMinutes === null ? "" : ` Age ${check.ageMinutes} min.`}`}
              tone={statusTone[check.status] || statusTone.missing}
            />
          ))}
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next evidence command</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.artifactHealth.nextAction || "Waiting for artifact freshness checks."}</p>
          <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
            {evidence?.artifactHealth.nextCommand || "No command needed."}
          </p>
        </div>
      </section>

      <div className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-black">Release evidence drilldown</p>
              <p className="mt-1 text-sm text-slate-400">
                Tracked sprint evidence markdown, newest files, and latest release-evidence folder state.
              </p>
            </div>
            <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.releaseEvidenceDrilldown.status || "missing"] || statusTone.missing}`}>
              {evidence?.releaseEvidenceDrilldown.status || "loading"}
            </span>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <MetricCard
              label="Evidence files"
              value={String(evidence?.releaseEvidenceDrilldown.fileCount ?? 0)}
              detail={`${evidence?.releaseEvidenceDrilldown.sprintCount ?? 0} sprint folders`}
              tone={statusTone[evidence?.releaseEvidenceDrilldown.status || "missing"] || statusTone.missing}
            />
            <MetricCard
              label="Latest sprint"
              value={evidence?.releaseEvidenceDrilldown.latestSprint || "loading"}
              detail={evidence?.releaseEvidenceDrilldown.latestModifiedAt ? formatTimestamp(evidence.releaseEvidenceDrilldown.latestModifiedAt) : "No tracked evidence yet."}
              tone={statusTone[evidence?.releaseEvidenceDrilldown.status || "missing"] || statusTone.missing}
            />
            <MetricCard
              label="Evidence root"
              value={evidence?.releaseEvidenceDrilldown.status || "loading"}
              detail={evidence?.releaseEvidenceDrilldown.root || "Waiting for evidence root."}
              tone={statusTone[evidence?.releaseEvidenceDrilldown.status || "missing"] || statusTone.missing}
            />
          </div>

          <div className="mt-5 space-y-3">
            {releaseEvidenceFiles.slice(0, 4).map((file) => (
              <div key={`${file.path}-${file.modifiedAt}`} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="font-semibold text-white">{file.title}</p>
                  <span className="w-fit rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">{file.sprint}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">Updated {formatTimestamp(file.modifiedAt)} · {file.bytes} bytes</p>
                <p className="mt-2 overflow-x-auto font-mono text-xs text-slate-500">{file.path}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 space-y-3">
            {(evidence?.releaseSprints.length ? evidence.releaseSprints : placeholderSprints()).slice(0, 3).map((sprint) => (
              <div key={sprint.sprint} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-semibold text-white">{sprint.sprint}</p>
                  <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">{sprint.fileCount} files</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">Latest update {formatTimestamp(sprint.latestModifiedAt)}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-black">Cost drivers</p>
            <a
              href="/api/control-center/evidence/report"
              className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100 transition hover:bg-cyan-300/20"
              target="_blank"
              rel="noreferrer"
            >
              Open latest markdown
            </a>
          </div>

          <div className="mt-4 space-y-3">
            {evidence?.apiCostReport.status === "ready" ? (
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Eval corpus</p>
                <p className="mt-2 text-sm text-slate-300">
                  {evidence.apiCostReport.recordsSeen} recorded cost rows across {evidence.apiCostReport.totalTokens} tokens.
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  Dataset cases: {evidence.apiCostReport.evalArtifacts.datasetCases}, prompt variants: {evidence.apiCostReport.evalArtifacts.promptVariantCount}.
                </p>
              </div>
            ) : null}

            {renderCostDrivers(evidence)}
          </div>

          <div className="mt-5 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-4 text-sm leading-6 text-cyan-100">
            The cost report and evidence pack stay file-backed, so the cockpit can show real sign-off state without a separate reporting service.
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">Runtime vs tracked evidence</p>
            <p className="mt-1 text-sm text-slate-400">
              Dashboard-level comparison between the current runtime evidence pack and the latest tracked release evidence.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.releaseComparison.status || "missing"] || statusTone.missing}`}>
            {evidence?.releaseComparison.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Relation"
            value={evidence?.releaseComparison.relation || "loading"}
            detail={evidence?.releaseComparison.minutesBetween === null ? "Waiting for both evidence surfaces." : `${evidence?.releaseComparison.minutesBetween ?? 0} minutes apart`}
            tone={statusTone[evidence?.releaseComparison.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Runtime JSON"
            value={evidence?.releaseComparison.currentExists ? "present" : "missing"}
            detail={evidence?.releaseComparison.currentModifiedAt ? formatTimestamp(evidence.releaseComparison.currentModifiedAt) : evidence?.releaseComparison.currentJsonPath || "No runtime JSON."}
            tone={statusTone[evidence?.releaseComparison.currentExists ? "ready" : "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Runtime generated"
            value={evidence?.releaseComparison.currentGeneratedAt ? "ready" : "missing"}
            detail={evidence?.releaseComparison.currentGeneratedAt ? formatTimestamp(evidence.releaseComparison.currentGeneratedAt) : "No generated_at_utc in runtime evidence."}
            tone={statusTone[evidence?.releaseComparison.currentGeneratedAt ? "ready" : "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Tracked latest"
            value={evidence?.releaseComparison.trackedExists ? "present" : "missing"}
            detail={evidence?.releaseComparison.trackedModifiedAt ? formatTimestamp(evidence.releaseComparison.trackedModifiedAt) : evidence?.releaseComparison.trackedPath || "No tracked markdown."}
            tone={statusTone[evidence?.releaseComparison.trackedExists ? "ready" : "missing"] || statusTone.missing}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Runtime evidence paths</p>
            <p className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.releaseComparison.currentJsonPath || "runtime/evidence/latest.json"}
            </p>
            <p className="mt-2 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {evidence?.releaseComparison.currentMarkdownPath || "runtime/evidence/latest.md"}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next comparison step</p>
            <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.releaseComparison.nextAction || "Waiting for release comparison."}</p>
            <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
              {evidence?.releaseComparison.nextCommand || "No command needed."}
            </p>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-black">Action audit drilldown</p>
            <p className="mt-1 text-sm text-slate-400">
              Recent Control Center action metadata from the audit JSONL, sanitized for cockpit review.
            </p>
          </div>
          <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${statusTone[evidence?.actionAuditDrilldown.status || "missing"] || statusTone.missing}`}>
            {evidence?.actionAuditDrilldown.status || "loading"}
          </span>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Audit records"
            value={String(evidence?.actionAuditDrilldown.recordCount ?? 0)}
            detail={actionAuditSampleDetail}
            tone={statusTone[evidence?.actionAuditDrilldown.status || "missing"] || statusTone.missing}
          />
          <MetricCard
            label="Dry runs"
            value={String(evidence?.actionAuditDrilldown.dryRunCount ?? 0)}
            detail={`${evidence?.actionAuditDrilldown.failedCount ?? 0} failed records`}
            tone={statusTone[evidence?.actionAuditDrilldown.failedCount ? "blocked" : "ready"] || statusTone.ready}
          />
          <MetricCard
            label="Authorization"
            value={`${evidence?.actionAuditDrilldown.authorizedCount ?? 0}/${evidence?.actionAuditDrilldown.deniedCount ?? 0}`}
            detail="Authorized / denied records."
            tone={statusTone[evidence?.actionAuditDrilldown.deniedCount ? "blocked" : "ready"] || statusTone.ready}
          />
          <MetricCard
            label="Invalid JSONL"
            value={String(evidence?.actionAuditDrilldown.invalidRecordCount ?? 0)}
            detail={
              evidence?.actionAuditDrilldown.truncated
                ? `Bounded tail read from ${evidence.actionAuditDrilldown.path}.`
                : evidence?.actionAuditDrilldown.path || configuredActionAuditPath
            }
            tone={statusTone[evidence?.actionAuditDrilldown.invalidRecordCount || evidence?.actionAuditDrilldown.truncated ? "warn" : "ready"] || statusTone.ready}
          />
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Counts</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {renderCountPills("Risk", evidence?.actionAuditDrilldown.riskCounts || {})}
              {renderCountPills("Action", evidence?.actionAuditDrilldown.actionCounts || {})}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recent records</p>
            <div className="mt-3 space-y-3">
              {actionAuditRecords.slice(0, 5).map((record) => (
                <div key={`${record.auditId}-${record.at}-${record.action}`} className="rounded-xl border border-white/10 bg-black/10 p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="font-mono text-xs text-cyan-100">{record.action}</p>
                    <span className="w-fit rounded-full bg-white/10 px-2 py-1 text-xs text-slate-300">{record.riskClass}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{record.summary}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {formatTimestamp(record.at)} · target {record.target} · role {record.actorRole} · ok {record.ok} · authorized {record.authorized}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Next audit step</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">{evidence?.actionAuditDrilldown.nextAction || "Waiting for action audit evidence."}</p>
          <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
            {evidence?.actionAuditDrilldown.nextCommand || "No command needed."}
          </p>
        </div>
      </section>

      <div className="mt-6 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
          <p className="text-sm font-black">Suggested next steps</p>
          <div className="mt-4 space-y-3">
            {(evidence?.recommendations.length ? evidence.recommendations : placeholderRecommendations()).map((item) => (
              <div key={item} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-slate-300">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
          <p className="text-sm font-black">Evidence links</p>
          <div className="mt-4 space-y-3">
            <EvidenceLink label="Latest evidence markdown" path="/api/control-center/evidence/report" />
            <EvidenceLink label="Latest API cost markdown" path="/api/control-center/evidence/api-cost-report" />
            <EvidenceLink label="Helper release gate" path={evidence?.otclientHelper.sourcePaths.releaseGate || "runtime/solteria_helper_dev/release_gate.json"} />
            <EvidenceLink label="Helper manifest" path={evidence?.otclientHelper.sourcePaths.manifest || "runtime/solteria_helper_dev/manifest.json"} />
            <EvidenceLink label="Helper live promotion" path={evidence?.otclientHelper.sourcePaths.livePromotion || "runtime/solteria_helper_dev/live_promotion.json"} />
            <EvidenceLink label="Helper BackgroundNoScreen" path={evidence?.otclientHelper.sourcePaths.backgroundStatus || "runtime/solteria_helper_dev/background_status.json"} />
            <EvidenceLink label="Helper P9 Conditions shadow" path={evidence?.otclientHelper.sourcePaths.conditionsShadowReplay || "runtime/solteria_helper_dev/conditions_shadow_replay.json"} />
            <EvidenceLink label="Engine Brain manifest" path={evidence?.engineBrain.sourcePaths.manifest || "AI/generated/manifest.json"} />
            <EvidenceLink label="Engine Brain guardrail" path={evidence?.engineBrain.sourcePaths.secretGuardrail || "AI/generated/SECRET_GUARDRAIL.json"} />
            <EvidenceLink label="P6 plugin handoff smoke" path={evidence?.engineBrain.sourcePaths.p6PluginHandoffSmoke || "runtime/control-center/p6-plugin-handoff-smoke.json"} />
            <EvidenceLink label="P7 operator brief" path={evidence?.engineBrain.sourcePaths.operatorBrief || "AI/generated/P7_OPERATOR_BRIEF.json"} />
            <EvidenceLink label="P7 cockpit smoke" path={evidence?.engineBrain.sourcePaths.p7CockpitSmoke || "runtime/control-center/p7-cockpit-smoke.json"} />
            <EvidenceLink label="P7 safe-write dry-run smoke" path={evidence?.engineBrain.sourcePaths.p7SafeWriteDryRunSmoke || "runtime/control-center/p7-safe-write-dry-run-smoke.json"} />
          </div>
        </section>
      </div>
    </article>
  )
}

function MetricCard({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return (
    <div className={`rounded-3xl border p-5 ${tone}`}>
      <p className="text-xs uppercase tracking-[0.22em] opacity-70">{label}</p>
      <h3 className="mt-4 text-2xl font-black tracking-tight">{value}</h3>
      <p className="mt-4 min-h-12 text-sm leading-6 opacity-75">{detail}</p>
    </div>
  )
}

function placeholderSprints() {
  return [
    { sprint: "sprint-056", fileCount: 0, latestModifiedAt: "loading" },
    { sprint: "sprint-055", fileCount: 0, latestModifiedAt: "loading" },
  ]
}

function placeholderReleaseEvidenceFiles() {
  return [
    { sprint: "loading", path: "releases/evidence", title: "Waiting for release evidence.", modifiedAt: "loading", bytes: 0 },
  ]
}

function placeholderActionAuditRecords() {
  return [
    {
      at: "loading",
      auditId: "loading",
      action: "waiting",
      target: "control-center",
      riskClass: "read_only",
      actorRole: "unknown",
      authorized: "n/a",
      ok: "n/a",
      dryRun: true,
      summary: "Waiting for Control Center action audit records.",
    },
  ]
}

function placeholderRecommendations() {
  return [
    "Generate the latest evidence pack with scripts/ops/release_evidence_pack.py.",
    "Run scripts/ops/api_cost_report.py after evals/runs changes land.",
    "Keep one fresh action audit entry visible from Control Center before sign-off.",
  ]
}

function placeholderArtifactChecks() {
  return [
    { name: "helper_manifest_age", status: "loading", detail: "Waiting for Helper manifest.", artifactPath: "", ageMinutes: null },
    { name: "helper_package_hash", status: "loading", detail: "Waiting for Helper package hash.", artifactPath: "", ageMinutes: null },
    { name: "helper_smoke_evidence", status: "loading", detail: "Waiting for Helper smoke evidence.", artifactPath: "", ageMinutes: null },
    { name: "helper_live_promotion", status: "loading", detail: "Waiting for Helper live promotion evidence.", artifactPath: "", ageMinutes: null },
    { name: "control_center_action_audit", status: "loading", detail: "Waiting for Control Center action audit.", artifactPath: "", ageMinutes: null },
  ]
}

function formatCheckName(value: string) {
  return value.replace(/^helper_/, "").replace(/^control_center_/, "").replace(/_/g, " ")
}

function renderCountPills(label: string, counts: Record<string, number>) {
  const entries = Object.entries(counts).slice(0, 4)
  if (!entries.length) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/10 p-3">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
        <p className="mt-2 text-sm text-slate-300">No records.</p>
      </div>
    )
  }

  return entries.map(([name, count]) => (
    <div key={`${label}-${name}`} className="rounded-xl border border-white/10 bg-black/10 p-3">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{name}</p>
      <p className="mt-1 text-xs text-slate-400">{count} records</p>
    </div>
  ))
}

function formatTimestamp(value: string) {
  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) return "not generated yet"
  return new Date(timestamp).toLocaleString()
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 B"
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`
}

function renderCostDrivers(evidence: ControlCenterEvidence | null) {
  const report = evidence?.apiCostReport
  const evalArtifacts = report?.evalArtifacts
  const categoryCounts = evalArtifacts?.categoryCounts || {}
  const promptVariants = evalArtifacts?.promptVariants || []
  const categories = Object.entries(categoryCounts)

  if (report?.status === "ready" && report.recordsSeen > 0) {
    return [
      "Runtime cost rows are available; the eval corpus still helps explain the likely hotspots.",
      `Prompt variants present: ${promptVariants.length ? promptVariants.join(", ") : "none"}.`,
    ].map((item) => (
      <div key={item} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-slate-300">
        {item}
      </div>
    ))
  }

  return (
    <>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">No runtime cost rows yet</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          The current cost report is anchored to the configured eval corpus, so these are the shapes that will drive the first real costs.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {(categories.length ? categories : [["dataset cases", 0]]).map(([label, count]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-black text-white">{count}</p>
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-slate-300">
        Prompt variants: {promptVariants.length ? promptVariants.join(", ") : "none"}
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-slate-300">
        Dataset cases: {evalArtifacts?.datasetCases ?? 0}
      </div>
    </>
  )
}

function EvidenceLink({ label, path }: { label: string; path: string }) {
  return (
    <a
      href={path}
      target="_blank"
      rel="noreferrer"
      className="block rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300 transition hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-cyan-100"
    >
      <span className="block text-xs uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <span className="mt-1 block font-mono text-xs text-slate-400">{path}</span>
    </a>
  )
}
