"use client"

import { useEffect, useMemo, useState } from "react"
import type { ControlCenterOps, VpsDiskDetail } from "@/lib/controlCenterOps"

type PanelMode = "all" | "vps" | "docker" | "bot" | "github"

type DetailState =
  | { state: "loading"; ops: null; error: null }
  | { state: "ready"; ops: ControlCenterOps; error: null }
  | { state: "error"; ops: null; error: string }

export default function ControlCenterDetailPanels({ mode = "all" }: { mode?: PanelMode }) {
  const [details, setDetails] = useState<DetailState>({ state: "loading", ops: null, error: null })
  const [diskHistory, setDiskHistory] = useState<Array<{ label: string; usePercent: number }>>([])

  useEffect(() => {
    let cancelled = false

    async function loadDetails() {
      try {
        const response = await fetch("/api/control-center/ops", { cache: "no-store" })
        const ops = (await response.json()) as ControlCenterOps
        if (cancelled) return
        setDetails({ state: "ready", ops, error: null })

        const disk = ops.details.vpsDisk
        if (disk) {
          setDiskHistory((previous) => {
            const next = [...previous, { label: new Date(ops.generatedAt).toLocaleTimeString(), usePercent: disk.usePercent }]
            return next.slice(-12)
          })
        }
      } catch (error) {
        if (!cancelled) {
          setDetails({
            state: "error",
            ops: null,
            error: error instanceof Error ? error.message : "Detail probe failed.",
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
      {show("vps") ? <VpsDiskPanel disk={ops?.details.vpsDisk || null} history={diskHistory} /> : null}
      {show("docker") ? <DockerImagesPanel images={ops?.details.dockerImages || []} /> : null}
      {show("bot") ? <BotLogsPanel lines={ops?.details.botLogs?.lines || []} /> : null}
      {show("github") ? <GithubRunsPanel runs={ops?.details.githubRuns || []} /> : null}
    </section>
  )
}

function VpsDiskPanel({ disk, history }: { disk: VpsDiskDetail | null; history: Array<{ label: string; usePercent: number }> }) {
  const usedGb = disk ? formatGb(disk.usedBytes) : "..."
  const availableGb = disk ? formatGb(disk.availableBytes) : "..."

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">VPS disk trend</p>
          <p className="mt-1 text-sm text-slate-400">Session trend from read-only disk probes.</p>
        </div>
        <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-200">
          {disk ? `${disk.usePercent}% used` : "loading"}
        </span>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Metric label="Used" value={usedGb} />
        <Metric label="Available" value={availableGb} />
        <Metric label="Mount" value={disk?.mount || "..."} />
      </div>

      <div className="mt-6 flex h-40 items-end gap-2 rounded-3xl border border-white/10 bg-[#0e1327] p-4">
        {(history.length ? history : [{ label: "loading", usePercent: 0 }]).map((point, index) => (
          <div key={`${point.label}-${index}`} className="flex flex-1 flex-col items-center gap-2">
            <div
              className="w-full rounded-t-xl bg-gradient-to-t from-cyan-500 to-fuchsia-400"
              style={{ height: `${Math.max(point.usePercent, 4)}%` }}
              title={`${point.label}: ${point.usePercent}%`}
            />
            <span className="text-[10px] text-slate-500">{point.usePercent}%</span>
          </div>
        ))}
      </div>
    </article>
  )
}

function DockerImagesPanel({ images }: { images: ControlCenterOps["details"]["dockerImages"] }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Docker image breakdown" label={`${images.length || "..."} images`} />
      <div className="mt-6 overflow-hidden rounded-3xl border border-white/10">
        <div className="grid grid-cols-[1.2fr_0.7fr_0.7fr] bg-white/[0.06] px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-400">
          <span>Image</span>
          <span>Age</span>
          <span>Size</span>
        </div>
        {(images.length ? images : placeholderRows()).map((image) => (
          <div key={`${image.repository}:${image.tag}:${image.imageId}`} className="grid grid-cols-[1.2fr_0.7fr_0.7fr] border-t border-white/10 px-4 py-3 text-sm">
            <span className="truncate font-semibold text-slate-100">{image.repository}:{image.tag}</span>
            <span className="text-slate-400">{image.createdSince}</span>
            <span className="text-cyan-100">{image.size}</span>
          </div>
        ))}
      </div>
    </article>
  )
}

function BotLogsPanel({ lines }: { lines: string[] }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="Bot logs preview" label={`${lines.length || "..."} lines`} />
      <pre className="mt-6 max-h-80 overflow-auto rounded-3xl border border-white/10 bg-[#090e1d] p-5 text-xs leading-6 text-slate-300">
        {(lines.length ? lines : ["Waiting for infra-bot logs..."]).join("\n")}
      </pre>
    </article>
  )
}

function GithubRunsPanel({ runs }: { runs: ControlCenterOps["details"]["githubRuns"] }) {
  const sortedRuns = useMemo(() => runs.slice(0, 10), [runs])

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <PanelHeader title="GitHub run list" label={`${sortedRuns.length || "..."} latest`} />
      <div className="mt-6 grid gap-3">
        {(sortedRuns.length ? sortedRuns : placeholderRuns()).map((run) => (
          <a
            key={run.databaseId || run.name}
            href={run.url || undefined}
            target="_blank"
            rel="noreferrer"
            className="rounded-3xl border border-white/10 bg-[#0e1327] p-4 transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-bold text-slate-100">{run.displayTitle || run.name}</p>
                <p className="mt-1 text-xs text-slate-500">{run.event} on {run.headBranch || "unknown branch"}</p>
              </div>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
                {run.status}/{run.conclusion || "pending"}
              </span>
            </div>
          </a>
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
        <p className="mt-1 text-sm text-slate-400">Live read-only detail panel.</p>
      </div>
      <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">{label}</span>
    </div>
  )
}

function formatGb(bytes: number): string {
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GiB`
}

function placeholderRows(): ControlCenterOps["details"]["dockerImages"] {
  return [{ repository: "loading", tag: "latest", imageId: "loading", createdSince: "...", size: "..." }]
}

function placeholderRuns(): ControlCenterOps["details"]["githubRuns"] {
  return [
    {
      databaseId: 0,
      name: "Loading GitHub runs",
      displayTitle: "Loading GitHub runs",
      status: "loading",
      conclusion: "",
      event: "...",
      headBranch: "",
      createdAt: "",
      url: "",
    },
  ]
}
