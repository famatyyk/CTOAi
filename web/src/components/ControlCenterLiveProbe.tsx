"use client"

import { useEffect, useState } from "react"
import type { ControlCenterSnapshot } from "@/lib/controlCenterSnapshot"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type ProbeState =
  | { state: "loading"; snapshot: null; error: null }
  | { state: "ready"; snapshot: ControlCenterSnapshot; error: null }
  | { state: "error"; snapshot: null; error: string }

export default function ControlCenterLiveProbe() {
  const [probe, setProbe] = useState<ProbeState>({ state: "loading", snapshot: null, error: null })

  useEffect(() => {
    let cancelled = false

    async function loadProbe() {
      try {
        const response = await fetchWithTimeout("/api/control-center", { cache: "no-store" }, 5000)
        const snapshot = (await response.json()) as ControlCenterSnapshot
        if (!cancelled) {
          setProbe({ state: "ready", snapshot, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setProbe({
            state: "error",
            snapshot: null,
            error: error instanceof Error ? error.message : "Control Center probe failed.",
          })
        }
      }
    }

    loadProbe()
    const timer = window.setInterval(loadProbe, 30000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const backend = probe.snapshot?.backend
  const reachable = backend?.reachable === true

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-black">Backend probe</p>
          <p className="mt-1 text-sm text-slate-400">Live read-only signal from the configured API.</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] ${
            probe.state === "loading"
              ? "bg-white/10 text-slate-300"
              : reachable
                ? "bg-cyan-300/10 text-cyan-200"
                : "bg-pink-400/10 text-pink-200"
          }`}
        >
          {probe.state === "loading" ? "loading" : reachable ? "online" : "offline"}
        </span>
      </div>

      <div className="mt-5 rounded-3xl border border-white/10 bg-[#0e1327] p-5">
        <span className="text-xs uppercase tracking-[0.22em] text-slate-500">Endpoint</span>
        <p className="mt-3 break-all text-sm text-cyan-100">{backend?.apiUrl || "Waiting for probe..."}</p>
        <p className="mt-4 text-sm leading-6 text-slate-400">
          {backend?.summary || probe.error || "Checking backend reachability..."}
        </p>
      </div>
    </article>
  )
}
