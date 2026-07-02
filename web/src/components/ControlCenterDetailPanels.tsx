"use client"

import { useEffect, useState } from "react"
import type { ControlCenterOps, LocalAuditAction } from "@/lib/controlCenterOps"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type PanelMode = "all" | "repo" | "release" | "cost" | "audit"

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
      {show("repo") ? <RepoHygienePanel details={ops?.details.repoHygiene || null} /> : null}
      {show("release") ? <ReleaseEvidencePanel details={ops?.details || null} /> : null}
      {show("cost") ? <ApiCostPanel details={ops?.details.apiCostReport || null} /> : null}
      {show("audit") ? <AuditPanel details={ops?.details.controlCenterAudit || null} /> : null}
      {mode === "all" && ops?.details.recommendations?.length ? <RecommendationsPanel items={ops.details.recommendations} /> : null}
    </section>
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

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Release evidence" label={latest ? "ready" : "missing"} />
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Files" value={String(details?.releaseEvidenceFileCount ?? 0)} />
        <Metric label="Sprints" value={String(sprints.length)} />
        <Metric label="Latest" value={latest ? latest.path.split(/[\\/]/).pop() || "n/a" : "n/a"} />
      </div>
      <div className="mt-6 grid gap-3">
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

function AuditPanel({ details }: { details: ControlCenterOps["details"]["controlCenterAudit"] | null }) {
  const status = details?.status || "loading"
  const recordCount = details?.recordCount ?? 0
  const sourcePath = details?.sourcePath || "runtime/control-center/action-audit.jsonl"
  const recentActions = details?.recentActions || []
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Control Center audit" label={status} />
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Metric label="Records" value={String(recordCount)} />
        <Metric label="Recent" value={String(recentActions.length)} />
      </div>
      <div className="mt-6 grid gap-3">
        {(recentActions.length ? recentActions : placeholderActions()).map((action, index) => (
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
        ))}
      </div>
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
