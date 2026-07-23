"use client"

import {
  CONTROL_CENTER_SCHEMA_VERSION,
  type ControlCenterCapabilityDetail,
  type EngineBrainDetail,
  type OperatorNextDetail,
} from "@/lib/controlCenterCapabilities"
import { type ControlCenterPublicOps, useControlCenterData } from "@/components/ControlCenterDataProvider"

type PanelMode = "all" | "repo" | "release" | "cost" | "audit" | "brain"

export default function ControlCenterDetailPanels({ mode = "all" }: { mode?: PanelMode }) {
  const details = useControlCenterData()
  const ops = details.data
  const operatorNext = loadCapability(ops, "operator-next")
  const engineBrain = loadCapability(ops, "engine-brain")
  const show = (panel: PanelMode) => mode === "all" || mode === panel

  if (details.state === "error") {
    return <div className="rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{details.error}</div>
  }

  return (
    <section className="grid gap-5">
      {mode === "all" ? <OperatorNextPanel details={operatorNext ? (operatorNext.value as OperatorNextDetail) : null} /> : null}
      {show("repo") ? <RepoHygienePanel details={ops?.details.repoHygiene || null} /> : null}
      {show("release") ? <ReleaseEvidencePanel details={ops?.details.releaseEvidence || null} /> : null}
      {show("brain") ? <EngineBrainPanel details={engineBrain ? (engineBrain.value as EngineBrainDetail) : null} /> : null}
      {show("cost") ? <ApiCostPanel details={ops?.details.apiCostReport || null} /> : null}
      {show("audit") ? <AuditPanel details={ops?.details.controlCenterAudit || null} /> : null}
      {mode === "all" && ops?.details.recommendations?.length ? <RecommendationsPanel items={ops.details.recommendations} /> : null}
    </section>
  )
}

/**
 * The existing /ops endpoint is a compatibility source.  Project it locally
 * into the same read-only capability shape and fail closed if a field is not
 * present; commands, source paths, identities, and raw audit data are never
 * rendered by these detail panels.
 */
function loadCapability(
  ops: ControlCenterPublicOps | null,
  capabilityId: "operator-next" | "engine-brain",
): ControlCenterCapabilityDetail | null {
  if (!ops) return null

  if (capabilityId === "operator-next") {
    const source = ops.details.operatorNext
    if (!source) return null
    return {
      schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
      capabilityId,
      collectedAt: ops.generatedAt,
      status: toCapabilityStatus(source.status),
      readOnly: true,
      value: {
        status: toCapabilityStatus(source.status),
        title: source.status === "ready" ? "Bounded evidence ready" : "Review evidence gate",
        detail:
          source.status === "ready"
            ? "Bounded local evidence is ready for review. No action is executed from this capability."
            : "Bounded local evidence is unavailable or needs review before any explicitly authorized follow-up.",
        lane: "evidence-review",
        riskClass: "read_only",
        readOnly: true,
      },
    }
  }

  const source = ops.details.engineBrain
  if (!source) return null
  return {
    schemaVersion: CONTROL_CENTER_SCHEMA_VERSION,
    capabilityId,
    collectedAt: ops.generatedAt,
    status: toCapabilityStatus(source.status),
    readOnly: true,
    value: {
      status: toCapabilityStatus(source.status),
      p6ReadinessStatus: source.p6ReadinessStatus || "missing",
      p6PluginHandoffStatus: toCapabilityStatus(source.p6PluginHandoffStatus),
      p7: {
        operatorBriefStatus: source.p7.operatorBriefStatus || "missing",
        actionReadinessStatus: source.p7.actionReadinessStatus || "missing",
        safeWriteToolDesignStatus: source.p7.safeWriteToolDesignStatus || "missing",
        decision: source.p7.decision || "missing",
        blockerCount: source.p7.blockerCount || 0,
        warningCount: source.p7.warningCount || 0,
        mcpWriteToolCount: source.p7.mcpWriteToolCount || 0,
        enabledSafeWriteToolCount: source.p7.enabledSafeWriteToolCount || 0,
        readySafeWriteAuditCount: source.p7.readySafeWriteAuditCount || 0,
        safeWriteAuditCount: source.p7.safeWriteAuditCount || 0,
        cockpitSmokeStatus: source.p7.cockpitSmokeStatus || "missing",
        dryRunSmokeStatus: source.p7.dryRunSmokeStatus || "missing",
        dryRunReadyCount: source.p7.dryRunReadyCount || 0,
        preflightReadyCount: source.p7.preflightReadyCount || 0,
        safeWriteToolCount: source.p7.safeWriteToolCount || 0,
        dryRunTools: [],
      },
      readOnly: true,
    },
  }
}

function toCapabilityStatus(value: string): "ready" | "warn" | "blocked" | "missing" {
  if (value === "ready" || value === "warn" || value === "blocked" || value === "missing") return value
  return "blocked"
}

function OperatorNextPanel({ details }: { details: OperatorNextDetail | null }) {
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
        <p className="mt-3 overflow-x-auto rounded-xl bg-black/20 p-3 font-mono text-xs text-cyan-100">Read-only review; no command is projected.</p>
      </div>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Bounded local evidence projection; source paths are intentionally not displayed.
      </p>
    </article>
  )
}

function RepoHygienePanel({ details }: { details: ControlCenterPublicOps["details"]["repoHygiene"] | null }) {
  const status = details?.status || "loading"
  const findingCount = details?.findingCount ?? 0
  const summary = details?.summary || {}
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
        Bounded local evidence; source paths are intentionally not displayed.
      </p>
    </article>
  )
}

function ReleaseEvidencePanel({ details }: { details: ControlCenterPublicOps["details"]["releaseEvidence"] | null }) {
  const status = details?.status || "loading"

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Release evidence" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Files" value={String(details?.fileCount ?? 0)} />
        <Metric label="Sprints" value={String(details?.sprintCount ?? 0)} />
        <Metric label="Relation" value={details?.relation || "loading"} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4">
        <p className="text-sm leading-6 text-slate-300">
          Latest bounded evidence update: {details?.latestUpdatedAt ? formatTimestamp(details.latestUpdatedAt) : "not available"}.
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          File names and source paths are intentionally not displayed in the browser.
        </p>
      </div>
    </article>
  )
}

function EngineBrainPanel({ details }: { details: EngineBrainDetail | null }) {
  const status = details?.status || "loading"
  const value = details
  // Keep these aliases local to the bounded detail projection. The public
  // endpoint carries only counts/statuses; individual tool identifiers remain
  // absent unless a capability detail has explicitly projected them.
  const p7EnabledSafeWriteToolCount = value?.p7.enabledSafeWriteToolCount ?? 0
  const p7ReadySafeWriteAuditCount = value?.p7.readySafeWriteAuditCount ?? 0
  const p7SafeWriteAuditCount = value?.p7.safeWriteAuditCount ?? 0
  const p7EnabledSafeWriteTools = value?.p7.dryRunTools || []
  const p7CockpitSmoke = value?.p7.cockpitSmokeStatus || "loading"
  const p7SafeWriteDryRunSmoke = value?.p7.dryRunSmokeStatus || "loading"
  const p7OperatorCockpitSummary = value
    ? `${p7EnabledSafeWriteToolCount} enabled safe-write tools; ${p7ReadySafeWriteAuditCount}/${p7SafeWriteAuditCount} audited.`
    : "No bounded P7 cockpit summary is available."
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Engine Brain" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-4 xl:grid-cols-6">
        <Metric label="P6 readiness" value={value?.p6ReadinessStatus || "loading"} />
        <Metric label="P7 brief" value={value ? value.p7.operatorBriefStatus : "loading"} />
        <Metric label="P7 action gate" value={value?.p7.actionReadinessStatus || "loading"} />
        <Metric label="P7 cockpit status" value={p7CockpitSmoke} />
        <Metric label="Dry-run tools" value={value ? `${value.p7.dryRunReadyCount}/${value.p7.safeWriteToolCount}` : "loading"} />
        <Metric label="P7 blockers" value={String(value?.p7.blockerCount ?? 0)} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">P7 decision</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">{value?.p7.decision || "No bounded P7 decision is available."}</p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P6 readiness</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {value ? `${value.p6ReadinessStatus}; plugin handoff ${value.p6PluginHandoffStatus}.` : "No P6 readiness projection yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 action gate</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {value
            ? `${value.p7.actionReadinessStatus}; ${p7OperatorCockpitSummary} ${value.p7.mcpWriteToolCount} MCP write tools declared.`
            : "No bounded P7 action gate is available."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 blockers</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {value ? `${value.p7.blockerCount} blockers; ${value.p7.warningCount} warnings.` : "No P7 blocker projection yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">P7 cockpit</p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          {value
            ? `${p7CockpitSmoke}; dry-run smoke ${p7SafeWriteDryRunSmoke}; preflight ${value.p7.preflightReadyCount}/${value.p7.safeWriteToolCount}.`
            : "No P7 cockpit projection yet."}
        </p>
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Dry-run tools</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {p7EnabledSafeWriteTools.length ? (
            p7EnabledSafeWriteTools.map((tool) => (
              <span key={`${tool.actionId}-${tool.mcpTool}`} className="rounded-full bg-cyan-300/10 px-3 py-1 font-mono text-xs text-cyan-100">
                {tool.mcpTool || tool.actionId}: {tool.auditStatus}
              </span>
            ))
          ) : (
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-400">
              {p7EnabledSafeWriteToolCount} bounded safe-write tools; identifiers are intentionally not projected.
            </span>
          )}
        </div>
      </div>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        This is a bounded, read-only projection. Source paths, commands, identities, reasons, and outputs are not rendered.
      </p>
    </article>
  )
}

function ApiCostPanel({ details }: { details: ControlCenterPublicOps["details"]["apiCostReport"] | null }) {
  const status = details?.status || "loading"
  const recordsSeen = details?.recordsSeen ?? 0
  const totalTokens = details?.totalTokens ?? 0
  const totalCostUsd = details?.totalCostUsd ?? 0
  const anomalyCount = details?.anomalyCount ?? 0
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
        Dataset cases: {details?.datasetCases ?? 0}, prompt variants: {details?.promptVariantCount ?? 0}
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] p-4 text-sm leading-6 text-slate-300">
        Bounded local evidence; source paths are intentionally not displayed.
      </div>
    </article>
  )
}

function AuditPanel({ details }: { details: ControlCenterPublicOps["details"]["controlCenterAudit"] | null }) {
  const status = details?.status || "loading"
  const recordCount = details?.recordCount ?? 0
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Control Center audit" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <Metric label="Records" value={String(recordCount)} />
        <Metric label="Dry runs" value={String(details?.dryRunCount ?? 0)} />
        <Metric label="Failed" value={String(details?.failedCount ?? 0)} />
        <Metric label="Invalid" value={String(details?.invalidRecordCount ?? 0)} />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <CountPills label="Risk" counts={details?.riskCounts || {}} />
        <CountPills label="Action" counts={details?.actionCounts || {}} />
      </div>
      <p className="mt-4 rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-xs leading-6 text-slate-400">
        Audit identities, reasons, outputs, commands, and source paths are intentionally not displayed.
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
