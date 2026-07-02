"use client"

import { useEffect, useState } from "react"
import type { ReactNode } from "react"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type LegacyResult = {
  ok: boolean
  status: number
  body: unknown
}

type LegacySnapshot = {
  generatedAt: string
  source: string
  capabilities: {
    dashboard: LegacyResult
    agentsStatus: LegacyResult
    releaseEvidence: LegacyResult
    commandDictionary: LegacyResult
    runnerLog: LegacyResult
  }
}

type LegacyState =
  | { state: "loading"; snapshot: null; error: null }
  | { state: "ready"; snapshot: LegacySnapshot; error: null }
  | { state: "error"; snapshot: null; error: string }

export default function ControlCenterLegacyPanels() {
  const [legacy, setLegacy] = useState<LegacyState>({ state: "loading", snapshot: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadLegacy() {
      try {
        const response = await fetchWithTimeout("/api/control-center/legacy", { cache: "no-store" }, 5000)
        const snapshot = (await response.json()) as LegacySnapshot
        if (!cancelled) {
          setLegacy({ state: "ready", snapshot, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setLegacy({
            state: "error",
            snapshot: null,
            error: error instanceof Error ? error.message : "Legacy parity probe failed.",
          })
        }
      }
    }

    loadLegacy()
    const timer = window.setInterval(loadLegacy, 60000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const snapshot = legacy.snapshot

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6 xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Legacy parity panels</p>
          <p className="mt-1 text-sm text-slate-400">Read-only migration of old console capabilities into Control Center.</p>
        </div>
        <span className="rounded-full bg-amber-300/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-amber-200">
          read-only
        </span>
      </div>

      {legacy.state === "error" ? (
        <div className="mt-6 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{legacy.error}</div>
      ) : null}

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <DashboardSummary result={snapshot?.capabilities.dashboard} />
        <AgentStatus result={snapshot?.capabilities.agentsStatus} />
        <ReleaseEvidence result={snapshot?.capabilities.releaseEvidence} />
        <CommandDictionary result={snapshot?.capabilities.commandDictionary} />
        <RunnerLog result={snapshot?.capabilities.runnerLog} />
      </div>
    </article>
  )
}

function DashboardSummary({ result }: { result?: LegacyResult }) {
  const body = asRecord(result?.body)
  const summary = asRecord(body.summary)
  const timeline = asRecord(body.timeline_summary)
  const statusContext = asRecord(body.status_context)

  return (
    <PanelCard title="Dashboard summary" result={result}>
      <MetricLine label="Status" value={String(body.status || "unknown")} />
      <MetricLine label="Message" value={String(body.status_message || statusContext.message || "No dashboard message")} />
      <MetricLine label="Latest day" value={String(timeline.latest_day || "n/a")} />
      <MetricLine label="Avg quality" value={String(timeline.avg_quality ?? "n/a")} />
      <MetricLine label="Healthy sections" value={listValue(summary.healthy_sections)} />
      <MetricLine label="Degraded sections" value={listValue(summary.degraded_sections)} />
    </PanelCard>
  )
}

function AgentStatus({ result }: { result?: LegacyResult }) {
  const body = asRecord(result?.body)
  return (
    <PanelCard title="Agent status" result={result}>
      <MetricLine label="Orchestrator" value={String(body.orchestrator || "unknown")} />
      <MetricLine label="Timer" value={String(body.orchestrator_timer || "unknown")} />
      <MetricLine label="DB" value={String(body.db || "unknown")} />
      <pre className="mt-4 max-h-40 overflow-auto rounded-2xl bg-[#090e1d] p-4 text-xs leading-6 text-slate-300">
        {String(body.last_runs_raw || "No recent agent runs.")}
      </pre>
    </PanelCard>
  )
}

function ReleaseEvidence({ result }: { result?: LegacyResult }) {
  const body = asRecord(result?.body)
  const release = asRecord(body.release_evidence)
  const source = asRecord(body.source)
  return (
    <PanelCard title="Release evidence" result={result}>
      <MetricLine label="Release state" value={String(body.release_state || "UNKNOWN")} />
      <MetricLine label="Evidence OK" value={String(body.ok ?? false)} />
      <MetricLine label="Status endpoint" value={String(source.status_endpoint || "n/a")} />
      <MetricLine label="Release endpoint" value={String(source.release_evidence_endpoint || "n/a")} />
      <MetricLine label="Proxy status" value={String(release.status || "n/a")} />
    </PanelCard>
  )
}

function CommandDictionary({ result }: { result?: LegacyResult }) {
  const body = asRecord(result?.body)
  const commands = Array.isArray(body.commands) ? body.commands.slice(0, 8) : []

  return (
    <PanelCard title="Command dictionary" result={result}>
      <MetricLine label="Version" value={String(body.version || "unknown")} />
      <MetricLine label="Source" value={String(body.source || "unknown")} />
      <MetricLine label="Count" value={String(body.count ?? commands.length)} />
      <div className="mt-4 grid gap-2">
        {commands.length ? commands.map((command, index) => <CommandRow key={index} command={command} />) : <p className="text-sm text-slate-500">No commands available.</p>}
      </div>
    </PanelCard>
  )
}

function RunnerLog({ result }: { result?: LegacyResult }) {
  const body = asRecord(result?.body)
  const output = String(body.stdout || body.stderr || "No runner log output.")

  return (
    <div className="xl:col-span-2">
      <PanelCard title="Runner log preview" result={result}>
        <pre className="max-h-72 overflow-auto rounded-2xl bg-[#090e1d] p-4 text-xs leading-6 text-slate-300">{output}</pre>
      </PanelCard>
    </div>
  )
}

function PanelCard({ title, result, children }: { title: string; result?: LegacyResult; children: ReactNode }) {
  const ok = result?.ok === true
  const statusLabel = result ? (ok ? "online" : `http ${result.status}`) : "loading"

  return (
    <section className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-black">{title}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${ok ? "bg-cyan-300/10 text-cyan-200" : "bg-amber-300/10 text-amber-200"}`}>
          {statusLabel}
        </span>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  )
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[0.42fr_1fr] gap-3 border-t border-white/10 py-2 text-sm first:border-t-0 first:pt-0">
      <span className="text-slate-500">{label}</span>
      <span className="break-words text-slate-200">{value}</span>
    </div>
  )
}

function CommandRow({ command }: { command: unknown }) {
  const data = asRecord(command)
  const name = String(data.name || data.id || data.command || "unnamed")
  const risk = String(data.risk || data.risk_class || "unknown")
  const description = String(data.description || data.label || "")

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold text-slate-100">{name}</span>
        <span className="rounded-full bg-white/10 px-2 py-1 text-xs text-slate-400">{risk}</span>
      </div>
      {description ? <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p> : null}
    </div>
  )
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function listValue(value: unknown): string {
  if (!Array.isArray(value)) return "none"
  return value.length ? value.map(String).join(", ") : "none"
}
