"use client"

import { useEffect, useState } from "react"
import type { ControlCenterOps, LocalAuditAction } from "@/lib/controlCenterOps"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type PanelMode = "all" | "repo" | "release" | "cost" | "audit" | "brain"

type DetailState =
  | { state: "loading"; ops: null; error: null }
  | { state: "ready"; ops: ControlCenterOps; error: null }
  | { state: "error"; ops: null; error: string }

export default function ControlCenterDetailPanels({ mode = "all" }: { mode?: PanelMode }) {
  const [details, setDetails] = useState<DetailState>({ state: "loading", ops: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadDetails() {
      try {
        const response = await fetchWithTimeout("/api/control-center/ops", { cache: "no-store" }, 5000)
        if (!response.ok) {
          throw new Error(`Local status probe failed with HTTP ${response.status}.`)
        }
        const ops = (await response.json()) as ControlCenterOps
        if (!cancelled) {
          setDetails({ state: "ready", ops, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setDetails({
            state: "error",
            ops: null,
            error: error instanceof Error ? error.message : "Local status probe failed.",
          })
        }
      }
    }

    loadDetails()
    const timer = window.setInterval(loadDetails, 60000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const ops = details.ops
  const show = (panel: PanelMode) => mode === "all" || mode === panel

  if (details.state === "error") {
    return <div className="rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{details.error}</div>
  }

  return (
    <section className="grid gap-5">
      {mode === "all" ? <OperatorNextPanel details={ops?.details.operatorNext || null} /> : null}
      {show("repo") ? <RepoHygienePanel details={ops?.details.repoHygiene || null} /> : null}
      {show("release") ? <ReleaseEvidencePanel details={ops?.details || null} /> : null}
      {show("brain") ? <EngineBrainPanel details={ops?.details.engineBrain || null} /> : null}
      {show("cost") ? <ApiCostPanel details={ops?.details.apiCostReport || null} /> : null}
      {show("audit") ? <AuditPanel details={ops?.details || null} /> : null}
      {mode === "all" && ops?.details.recommendations?.length ? <RecommendationsPanel items={ops.details.recommendations} /> : null}
    </section>
  )
}

function OperatorNextPanel({ details }: { details: ControlCenterOps["details"]["operatorNext"] | null }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Operator next" label={details?.status || "loading"} />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Lane" value={details?.lane || "loading"} />
        <Metric label="Risk" value={details?.riskClass || "read_only"} />
        <Metric label="Status" value={details?.status || "loading"} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4">
        <p className="text-sm font-black text-slate-100">{details?.title || "Waiting for evidence."}</p>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          {details?.detail || "Collecting local evidence before choosing the next operator step."}
        </p>
        <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
          {details?.command || "Manual review only."}
        </p>
      </div>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Source: {details?.sourcePath || "Waiting for source evidence."}
      </p>
    </article>
  )
}

function RepoHygienePanel({ details }: { details: ControlCenterOps["details"]["repoHygiene"] | null }) {
  const status = details?.status || "loading"
  const findingCount = details?.findingCount ?? 0
  const summary: ControlCenterOps["details"]["repoHygiene"]["summary"] = details?.summary || {}
  const sourcePath = details?.sourcePath || "runtime/repo-hygiene/local-pr-quality.json"
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Repo hygiene" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Findings" value={String(findingCount)} />
        <Metric label="Private" value={String(summary.private_count ?? 0)} />
        <Metric label="Public" value={String(summary.public_count ?? 0)} />
      </div>
      <p className="mt-4 text-sm leading-6 text-slate-400">
        Review count: <span className="text-slate-100">{String(summary.review_count ?? 0)}</span>
      </p>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Source: {sourcePath}
      </p>
    </article>
  )
}

function ReleaseEvidencePanel({ details }: { details: ControlCenterOps["details"] | null }) {
  const latest = details?.latestReleaseEvidence || null
  const sprints = details?.releaseSprints || []
  const drilldown = details?.releaseEvidenceDrilldown || null
  const comparison = details?.releaseComparison || null
  const recentFiles = drilldown?.recentFiles || []

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Release evidence" label={latest ? "ready" : "missing"} />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Files" value={String(drilldown?.fileCount ?? details?.releaseEvidenceFileCount ?? 0)} />
        <Metric label="Sprints" value={String(drilldown?.sprintCount ?? sprints.length)} />
        <Metric label="Relation" value={comparison?.relation || "loading"} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Latest tracked markdown</p>
            <p className="mt-2 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {latest ? latest.path : "No release evidence markdown found yet."}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Runtime evidence</p>
            <p className="mt-2 overflow-x-auto font-mono text-xs leading-6 text-slate-300">
              {comparison?.currentJsonPath || "runtime/evidence/latest.json"}
            </p>
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          {comparison?.nextAction || drilldown?.nextAction || "Waiting for release evidence drilldown."}
        </p>
      </div>
      <div className="mt-6 grid gap-3">
        {recentFiles.length ? (
          recentFiles.slice(0, 4).map((file) => (
            <div key={`${file.path}-${file.modifiedAt}`} className="rounded-2xl border border-white/10 bg-[#0e1327] p-4">
              <div className="flex items-center justify-between gap-4">
                <p className="font-semibold text-slate-100">{file.title}</p>
                <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">{file.sprint}</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">Updated {formatTimestamp(file.modifiedAt)} · {file.bytes} bytes</p>
              <p className="mt-2 overflow-x-auto font-mono text-xs text-slate-500">{file.path}</p>
            </div>
          ))
        ) : null}
        {sprints.length ? (
          sprints.map((sprint) => (
            <div key={sprint.sprint} className="rounded-2xl border border-white/10 bg-[#0e1327] p-4">
              <div className="flex items-center justify-between gap-4">
                <p className="font-semibold text-slate-100">{sprint.sprint}</p>
                <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-100">{sprint.fileCount} files</span>
              </div>
              <p className="mt-2 text-sm text-slate-400">Latest update {formatTimestamp(sprint.latestModifiedAt)}</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-500">No release evidence folders found yet.</p>
        )}
      </div>
    </article>
  )
}

function EngineBrainPanel({ details }: { details: ControlCenterOps["details"]["engineBrain"] | null }) {
  const status = details?.status || "loading"
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Engine Brain" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-4 xl:grid-cols-8">
        <Metric label="P6" value={details?.p6ReadinessStatus || "loading"} />
        <Metric label="P6 smoke" value={details?.p6PluginHandoff.smokeStatus || "loading"} />
        <Metric label="P7" value={details?.p7OperatorBriefStatus || "loading"} />
        <Metric label="Action gate" value={details?.p7ActionReadinessStatus || "loading"} />
        <Metric label="Tool design" value={details?.p7SafeWriteToolDesignStatus || "loading"} />
        <Metric label="MCP tools" value={String(details?.p7EnabledSafeWriteToolCount ?? 0)} />
        <Metric
          label="Safe audit"
          value={
            details?.p7SafeWriteAuditCount
              ? `${details.p7ReadySafeWriteAuditCount}/${details.p7SafeWriteAuditCount}`
              : details?.p7SafeWriteAudit.status || "loading"
          }
        />
        <Metric label="P7 smoke" value={details?.p7CockpitSmoke.status || "loading"} />
        <Metric
          label="Dry-run smoke"
          value={
            details
              ? `${details.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${details.p7SafeWriteDryRunSmoke.safeWriteToolCount}; preflight ${details.p7SafeWriteDryRunSmoke.preflightReadyCount}/${details.p7SafeWriteDryRunSmoke.safeWriteToolCount}`
              : "loading"
          }
        />
        <Metric label="Blockers" value={String(details?.p7HardBlockerCount ?? 0)} />
        <Metric label="Warnings" value={String(details?.p7WarningCount ?? 0)} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">P7 decision</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">{details?.p7Decision || "No generated P7 decision yet."}</p>
        <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">
          {details?.p7NextSafeCommand || ".\\ctoa.ps1 brain refresh"}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 cockpit status</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details?.p7OperatorCockpitSummary || "No generated P7 cockpit summary yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P6 plugin handoff smoke</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details
            ? `${details.p6PluginHandoff.smokeStatus}; ${details.p6PluginHandoff.smokePassedCount}/${details.p6PluginHandoff.smokeCheckCount} checks; discovery ${details.p6PluginHandoff.currentThreadToolDiscoveryStatus}; ${details.p6PluginHandoff.freshThreadVerificationStatus}`
            : "No generated P6 plugin handoff smoke yet."}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {(details?.p7EnabledSafeWriteTools.length ? details.p7EnabledSafeWriteTools : []).map((tool) => (
            <span key={`${tool.actionId}-${tool.mcpTool}`} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
              {tool.mcpTool || tool.actionId}: {tool.auditStatus}
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 action readiness</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details
            ? `${details.p7ActionReadinessDecision || "missing"}; ${details.p7ActionAuditedCandidateCount}/${details.p7ActionCandidateCount} audited; ${details.p7McpWriteToolCount} MCP write tools`
            : "No generated P7 action readiness yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Safe-write design</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details
            ? `${details.p7SafeWriteToolDesignDecision || "missing"}; ${details.p7SafeWriteToolProposedMcpTool || "n/a"}; MCP enabled ${details.p7SafeWriteToolMcpEnabled}`
            : "No generated safe-write design yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Safe-write audit</p>
        <div className="mt-2 grid gap-2">
          {(details?.p7SafeWriteAudits.length ? details.p7SafeWriteAudits : details?.p7SafeWriteAudit ? [details.p7SafeWriteAudit] : []).map((audit) => (
            <p key={`${audit.expectedAction}-${audit.auditId || audit.proposedMcpTool}`} className="text-sm leading-6 text-slate-300">
              {audit.latestAt
                ? `${audit.proposedMcpTool || audit.expectedAction}; ${audit.riskClass}; ${audit.dryRun ? "dry-run" : "confirmed"}; ok ${audit.ok}; authorized ${audit.authorized}`
                : audit.nextAction}
            </p>
          ))}
        </div>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 cockpit smoke</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details
            ? `${details.p7CockpitSmoke.status}; ${details.p7CockpitSmoke.passedCount}/${details.p7CockpitSmoke.checkCount} checks; safe-write audits ${details.p7CockpitSmoke.readySafeWriteAuditCount}/${details.p7CockpitSmoke.expectedSafeWriteAuditCount}`
            : "No generated P7 cockpit smoke yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 safe-write dry-run smoke</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {details
            ? `${details.p7SafeWriteDryRunSmoke.status}; ${details.p7SafeWriteDryRunSmoke.dryRunReadyCount}/${details.p7SafeWriteDryRunSmoke.safeWriteToolCount} dry-run tools; ${details.p7SafeWriteDryRunSmoke.preflightReadyCount}/${details.p7SafeWriteDryRunSmoke.safeWriteToolCount} preflight; ${details.p7SafeWriteDryRunSmoke.bootstrapAllowedCount} bootstrap; ${details.p7SafeWriteDryRunSmoke.passedCount}/${details.p7SafeWriteDryRunSmoke.checkCount} checks`
            : "No generated P7 safe-write dry-run smoke yet."}
        </p>
      </div>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Source: {details?.sourcePaths.operatorBrief || "AI/generated/P7_OPERATOR_BRIEF.json"}; P6 smoke: {details?.sourcePaths.p6PluginHandoffSmoke || "runtime/control-center/p6-plugin-handoff-smoke.json"}; P7 smoke: {details?.sourcePaths.p7CockpitSmoke || "runtime/control-center/p7-cockpit-smoke.json"}; dry-run: {details?.sourcePaths.p7SafeWriteDryRunSmoke || "runtime/control-center/p7-safe-write-dry-run-smoke.json"}
      </p>
    </article>
  )
}

function ApiCostPanel({ details }: { details: ControlCenterOps["details"]["apiCostReport"] | null }) {
  const status = details?.status || "loading"
  const recordsSeen = details?.recordsSeen ?? 0
  const totalTokens = details?.totalTokens ?? 0
  const totalCostUsd = details?.totalCostUsd ?? 0
  const anomalyCount = details?.anomalyCount ?? 0
  const evalArtifacts = details?.evalArtifacts || {
    datasetPath: "evals/azure-activity-agent-eval-dataset.template.jsonl",
    datasetCases: 0,
    categoryCounts: {},
    priorityCounts: {},
    promptVariantsDir: "evals/prompt-variants",
    promptVariantCount: 0,
    promptVariants: [],
  }
  const sourcePath = details?.sourcePath || "runtime/api-cost/latest.json"
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="API cost report" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <Metric label="Rows" value={String(recordsSeen)} />
        <Metric label="Tokens" value={String(totalTokens)} />
        <Metric label="Cost" value={`$${totalCostUsd.toFixed(2)}`} />
        <Metric label="Anomalies" value={String(anomalyCount)} />
      </div>
      <div className="mt-6 rounded-2xl border border-white/10 bg-[#0e1327] p-4 text-sm leading-6 text-slate-300">
        Dataset cases: {evalArtifacts.datasetCases}, prompt variants: {evalArtifacts.promptVariantCount}
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4 text-sm leading-6 text-slate-300">
        Source: {sourcePath}
      </div>
    </article>
  )
}

function AuditPanel({ details }: { details: ControlCenterOps["details"] | null }) {
  const audit = details?.controlCenterAudit || null
  const drilldown = details?.actionAuditDrilldown || null
  const status = drilldown?.status || audit?.status || "loading"
  const recordCount = drilldown?.recordCount ?? audit?.recordCount ?? 0
  const sourcePath = drilldown?.path || audit?.sourcePath || "runtime/control-center/action-audit.jsonl"
  const recentRecords = drilldown?.recentRecords || []
  const recentActions = audit?.recentActions || []
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Control Center audit" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <Metric label="Records" value={String(recordCount)} />
        <Metric label="Dry runs" value={String(drilldown?.dryRunCount ?? 0)} />
        <Metric label="Failed" value={String(drilldown?.failedCount ?? 0)} />
        <Metric label="Invalid" value={String(drilldown?.invalidRecordCount ?? 0)} />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <CountPills label="Risk" counts={drilldown?.riskCounts || {}} />
        <CountPills label="Action" counts={drilldown?.actionCounts || {}} />
      </div>
      <div className="mt-6 grid gap-3">
        {recentRecords.length ? (
          recentRecords.map((record) => (
            <div key={`${record.auditId}-${record.at}-${record.action}`} className="rounded-2xl border border-white/10 bg-[#0e1327] p-4">
              <div className="flex items-center justify-between gap-4">
                <p className="font-semibold text-slate-100">{record.action || "unknown action"}</p>
                <span className={`rounded-full px-3 py-1 text-xs font-bold ${record.ok === "yes" ? "bg-cyan-300/10 text-cyan-100" : "bg-amber-300/10 text-amber-100"}`}>
                  {record.dryRun ? "dry-run" : "live"}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-400">
                {record.target || "n/a"} · {formatTimestamp(record.at)} · {record.riskClass || "unknown risk"}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-300">{record.summary}</p>
              <p className="mt-2 text-xs text-slate-500">
                role {record.actorRole} · ok {record.ok} · authorized {record.authorized}
              </p>
            </div>
          ))
        ) : (
          (recentActions.length ? recentActions : placeholderActions()).map((action, index) => (
          <div key={`${action.action}-${index}`} className="rounded-2xl border border-white/10 bg-[#0e1327] p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-semibold text-slate-100">{action.action || "unknown action"}</p>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${action.ok ? "bg-cyan-300/10 text-cyan-100" : "bg-amber-300/10 text-amber-100"}`}>
                {action.dryRun ? "dry-run" : "live"}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-400">
              {action.target || "n/a"} · {action.at || "unknown time"}
            </p>
            {action.reason ? <p className="mt-2 text-sm leading-6 text-slate-300">{action.reason}</p> : null}
          </div>
          ))
        )}
      </div>
      <p className="mt-4 text-sm leading-6 text-slate-400">
        {drilldown?.nextAction || "Waiting for action audit drilldown."}
      </p>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Source: {sourcePath}
      </p>
    </article>
  )
}

function RecommendationsPanel({ items }: { items: string[] }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Suggested next steps" label="local evidence" />
      <div className="mt-5 space-y-3">
        {items.map((item) => (
          <div key={item} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-slate-300">
            {item}
          </div>
        ))}
      </div>
    </article>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-black tracking-tight text-white">{value}</p>
    </div>
  )
}

function CountPills({ label, counts }: { label: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).slice(0, 4)
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0e1327] p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {entries.length ? (
          entries.map(([name, count]) => (
            <span key={`${label}-${name}`} className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
              {name}: {count}
            </span>
          ))
        ) : (
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-500">No records</span>
        )}
      </div>
    </div>
  )
}

function PanelHeader({ title, label }: { title: string; label: string }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-black">{title}</p>
        <p className="mt-1 text-sm text-slate-400">Local file-backed status panel.</p>
      </div>
      <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">{label}</span>
    </div>
  )
}

function formatTimestamp(value: string) {
  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) return "not generated yet"
  return new Date(timestamp).toLocaleString()
}

function placeholderActions(): LocalAuditAction[] {
  return [
    {
      at: "loading",
      auditId: "",
      actor: "",
      actorRole: "",
      action: "loading",
      target: "control-center",
      riskClass: "",
      minimumRole: "",
      dryRun: true,
      ok: false,
      authorized: false,
      reason: "",
      outputPreview: "",
    },
  ]
}
