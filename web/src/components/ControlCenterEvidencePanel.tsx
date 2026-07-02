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
  ready: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  missing: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  warn: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  FAIL: "border-pink-300/30 bg-pink-300/10 text-pink-100",
}

export default function ControlCenterEvidencePanel() {
  const [state, setState] = useState<EvidenceState>({ state: "loading", evidence: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadEvidence() {
      try {
        const response = await fetchWithTimeout("/api/control-center/evidence", { cache: "no-store" }, 5000)
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

      <div className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
          <p className="text-sm font-black">Release sprints</p>
          <div className="mt-4 space-y-3">
            {(evidence?.releaseSprints.length ? evidence.releaseSprints : placeholderSprints()).map((sprint) => (
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

function placeholderRecommendations() {
  return [
    "Generate the latest evidence pack with scripts/ops/release_evidence_pack.py.",
    "Run scripts/ops/api_cost_report.py after evals/runs changes land.",
    "Keep one fresh action audit entry visible from Control Center before sign-off.",
  ]
}

function formatTimestamp(value: string) {
  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) return "not generated yet"
  return new Date(timestamp).toLocaleString()
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
