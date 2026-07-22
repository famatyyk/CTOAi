"use client"

import { type ControlCenterPublicOps, useControlCenterData } from "@/components/ControlCenterDataProvider"

type PublicOpsStatus = ControlCenterPublicOps["tiles"][number]["status"]

const toneClass: Record<PublicOpsStatus, string> = {
  online: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  warning: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  offline: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  unknown: "border-white/10 bg-white/[0.05] text-slate-200",
}

const dotClass: Record<PublicOpsStatus, string> = {
  online: "bg-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.8)]",
  warning: "bg-amber-300 shadow-[0_0_18px_rgba(252,211,77,0.7)]",
  offline: "bg-pink-400 shadow-[0_0_18px_rgba(244,114,182,0.7)]",
  unknown: "bg-slate-500",
}

/**
 * Renders the one shared, server-projected public read model.  This component
 * intentionally knows nothing about raw ops fields such as source paths,
 * audit details, identities, commands, or prose from local evidence.
 */
export default function ControlCenterOpsGrid() {
  const dataState = useControlCenterData()
  const tiles = dataState.data?.tiles.length ? dataState.data.tiles : placeholderTiles()

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Local status tiles</p>
          <p className="mt-1 text-sm text-slate-400">Bounded status from the authenticated Control Center projection.</p>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
          {dataState.state === "loading" ? "loading" : dataState.data ? formatUpdatedAt(dataState.data.generatedAt) : "offline"}
        </span>
      </div>

      {dataState.state === "error" ? (
        <div className="mt-6 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{dataState.error}</div>
      ) : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {tiles.map((tile) => (
          <div key={tile.id} className={`rounded-3xl border p-5 ${toneClass[tile.status]}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] opacity-70">{tile.label}</p>
                <h3 className="mt-4 text-xl font-black tracking-tight">{tile.status}</h3>
              </div>
              <span className={`mt-1 h-3 w-3 rounded-full ${dotClass[tile.status]}`} />
            </div>
            <p className="mt-4 min-h-12 text-sm leading-6 opacity-75">Bounded status; operational details are intentionally not displayed.</p>
          </div>
        ))}
      </div>
    </article>
  )
}

function placeholderTiles(): ControlCenterPublicOps["tiles"] {
  return [
    { id: "repo-hygiene", label: "Repo hygiene", status: "unknown" },
    { id: "release-evidence", label: "Release evidence", status: "unknown" },
    { id: "api-cost", label: "API cost report", status: "unknown" },
    { id: "control-center-audit", label: "Control Center audit", status: "unknown" },
  ]
}

function formatUpdatedAt(value: string) {
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? "updated" : `updated ${new Date(timestamp).toLocaleTimeString()}`
}
