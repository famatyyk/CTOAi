"use client"

import { useEffect, useState } from "react"
import type { ControlCenterOps, OpsTile } from "@/lib/controlCenterOps"

type OpsState =
  | { state: "loading"; ops: null; error: null }
  | { state: "ready"; ops: ControlCenterOps; error: null }
  | { state: "error"; ops: null; error: string }

const toneClass: Record<OpsTile["status"], string> = {
  online: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  warning: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  offline: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  unknown: "border-white/10 bg-white/[0.05] text-slate-200",
}

const dotClass: Record<OpsTile["status"], string> = {
  online: "bg-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.8)]",
  warning: "bg-amber-300 shadow-[0_0_18px_rgba(252,211,77,0.7)]",
  offline: "bg-pink-400 shadow-[0_0_18px_rgba(244,114,182,0.7)]",
  unknown: "bg-slate-500",
}

export default function ControlCenterOpsGrid() {
  const [ops, setOps] = useState<OpsState>({ state: "loading", ops: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadOps() {
      try {
        const response = await fetch("/api/control-center/ops", { cache: "no-store" })
        const data = (await response.json()) as ControlCenterOps
        if (!cancelled) {
          setOps({ state: "ready", ops: data, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setOps({
            state: "error",
            ops: null,
            error: error instanceof Error ? error.message : "Ops probe failed.",
          })
        }
      }
    }

    loadOps()
    const timer = window.setInterval(loadOps, 45000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const tiles = ops.ops?.tiles || []

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Live ops tiles</p>
          <p className="mt-1 text-sm text-slate-400">Read-only probes for VPS, Docker, bot runtime and GitHub CI.</p>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
          {ops.state === "loading" ? "loading" : ops.ops ? `updated ${new Date(ops.ops.generatedAt).toLocaleTimeString()}` : "offline"}
        </span>
      </div>

      {ops.state === "error" ? (
        <div className="mt-6 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{ops.error}</div>
      ) : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {(tiles.length ? tiles : placeholderTiles()).map((tile) => (
          <div key={tile.id} className={`rounded-3xl border p-5 ${toneClass[tile.status]}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] opacity-70">{tile.label}</p>
                <h3 className="mt-4 text-xl font-black tracking-tight">{tile.headline}</h3>
              </div>
              <span className={`mt-1 h-3 w-3 rounded-full ${dotClass[tile.status]}`} />
            </div>
            <p className="mt-4 min-h-12 text-sm leading-6 opacity-75">{tile.detail}</p>
            <p className="mt-5 border-t border-white/10 pt-3 text-xs opacity-60">{tile.source}</p>
          </div>
        ))}
      </div>
    </article>
  )
}

function placeholderTiles(): OpsTile[] {
  const updatedAt = new Date().toISOString()
  return [
    {
      id: "vps",
      label: "VPS disk",
      status: "unknown",
      headline: "Loading",
      detail: "Waiting for SSH read-only probe.",
      source: "ssh df -h /",
      updatedAt,
    },
    {
      id: "docker",
      label: "Docker store",
      status: "unknown",
      headline: "Loading",
      detail: "Waiting for Docker storage report.",
      source: "ssh docker system df",
      updatedAt,
    },
    {
      id: "bot",
      label: "Bot runtime",
      status: "unknown",
      headline: "Loading",
      detail: "Waiting for infra-bot container status.",
      source: "ssh docker ps",
      updatedAt,
    },
    {
      id: "github",
      label: "GitHub CI",
      status: "unknown",
      headline: "Loading",
      detail: "Waiting for GitHub Actions status.",
      source: "gh run list",
      updatedAt,
    },
  ]
}
