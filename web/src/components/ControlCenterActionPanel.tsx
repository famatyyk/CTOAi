"use client"

import { useEffect, useMemo, useState } from "react"
import type {
  ControlCenterActionCapability,
  ControlCenterActionCapabilityResponse,
  ControlCenterActionResultProjection,
} from "@/lib/controlCenterActions"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type ActionLoadState =
  | { state: "loading"; capabilities: ControlCenterActionCapability[]; error: null }
  | { state: "ready"; capabilities: ControlCenterActionCapability[]; error: null }
  | { state: "error"; capabilities: ControlCenterActionCapability[]; error: string }

const riskTone: Record<ControlCenterActionCapability["riskClass"], string> = {
  read_only: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  safe_write: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
  guarded_write: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  dangerous: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  forbidden_ui: "border-slate-300/20 bg-slate-300/10 text-slate-300",
}

function preflightTone(status: "ready" | "blocked") {
  return status === "ready" ? "text-emerald-100" : "text-amber-100"
}

export default function ControlCenterActionPanel({ target }: { target?: ControlCenterActionCapability["target"] }) {
  const [loadState, setLoadState] = useState<ActionLoadState>({ state: "loading", capabilities: [], error: null })
  const [activeActionId, setActiveActionId] = useState("")
  const [confirmation, setConfirmation] = useState("")
  const [reason, setReason] = useState("")
  const [running, setRunning] = useState("")
  const [result, setResult] = useState<ControlCenterActionResultProjection | null>(null)
  const [proofs, setProofs] = useState<Record<string, string>>({})
  const [error, setError] = useState("")
  const [refreshTick, setRefreshTick] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function loadCapabilities() {
      try {
        const response = await fetchWithTimeout("/api/control-center/actions", { cache: "no-store", credentials: "include" }, 5000)
        const data = (await response.json()) as ControlCenterActionCapabilityResponse & { error?: string }
        if (!response.ok) throw new Error(data.error || "Action capability engine is unavailable.")
        if (data.schemaVersion !== 2 || !Array.isArray(data.capabilities)) {
          throw new Error("Action capability engine returned an unsupported schema.")
        }
        if (!cancelled) setLoadState({ state: "ready", capabilities: data.capabilities, error: null })
      } catch (loadError) {
        if (!cancelled) {
          setLoadState({
            state: "error",
            capabilities: [],
            error: loadError instanceof Error ? loadError.message : "Action capability engine failed to load.",
          })
        }
      }
    }

    loadCapabilities()
    return () => {
      cancelled = true
    }
  }, [refreshTick])

  const capabilities = useMemo(
    () => loadState.capabilities.filter((action) => !target || action.target === target),
    [loadState.capabilities, target],
  )
  const activeAction = capabilities.find((action) => action.id === activeActionId) || null
  const activeProof = activeAction ? proofs[activeAction.id] : undefined
  const activeExecutionReady = Boolean(activeAction && activeProof && result?.actionId === activeAction.id && result.preflight.executeAllowed)

  async function runAction(action: ControlCenterActionCapability, dryRun: boolean) {
    setRunning(action.id)
    setError("")
    if (dryRun) setResult(null)

    try {
      const response = await fetch("/api/control-center/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          actionId: action.id,
          confirmation: dryRun ? undefined : confirmation,
          reason: dryRun ? undefined : reason,
          proofId: dryRun ? undefined : proofs[action.id],
          dryRun,
        }),
      })
      const data = (await response.json()) as {
        ok: boolean
        error?: string
        result?: ControlCenterActionResultProjection
      }
      if (!response.ok || !data.result) throw new Error(data.error || "Action capability failed.")

      setResult(data.result)
      if (data.result.dryRun && data.result.ok && data.result.proofId) {
        setProofs((current) => ({ ...current, [action.id]: data.result?.proofId || "" }))
      } else if (!data.result.dryRun) {
        setProofs((current) => {
          const next = { ...current }
          delete next[action.id]
          return next
        })
      }
      if (!data.result.dryRun) {
        setConfirmation("")
        setReason("")
        setActiveActionId("")
      }
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Action capability failed.")
    } finally {
      setRunning("")
    }
  }

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-black">Action capability engine</p>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
            Bounded local evidence refreshes are dry-run-first. A validated proof is scoped to one action and one signed-in operator for 15 minutes.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
            {loadState.state === "loading" ? "loading" : `${capabilities.length} capabilities`}
          </span>
          <button
            type="button"
            onClick={() => setRefreshTick((value) => value + 1)}
            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            Refresh capability state
          </button>
        </div>
      </div>

      <p className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
        Identity and command details are not projected to the browser. Runtime, P7 registration, confirmation, and audit gates are enforced on the server.
      </p>

      {loadState.state === "error" ? (
        <div className="mt-5 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-4 text-sm text-pink-100">{loadState.error}</div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {capabilities.map((action) => {
          const { preflight } = action
          const hasProof = Boolean(proofs[action.id])
          return (
            <div key={action.id} className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-base font-black text-white">{action.label}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{action.description}</p>
                </div>
                <span className={`whitespace-nowrap rounded-full border px-3 py-1 text-xs font-bold ${riskTone[action.riskClass]}`}>
                  {action.riskClass}
                </span>
              </div>

              <dl className="mt-4 grid gap-2 text-sm leading-6 text-slate-400">
                <div>
                  <dt className="inline text-xs uppercase tracking-[0.16em] text-slate-500">Effect: </dt>
                  <dd className="inline">{action.effect}</dd>
                </div>
                <div>
                  <dt className="inline text-xs uppercase tracking-[0.16em] text-slate-500">Evidence: </dt>
                  <dd className="inline">{action.evidence}</dd>
                </div>
                <div className={preflightTone(preflight.status)}>
                  <dt className="inline text-xs uppercase tracking-[0.16em] text-slate-500">Preflight: </dt>
                  <dd className="inline">
                    {preflight.status}; execution {preflight.executeAllowed ? "ready" : "requires a fresh dry-run proof"}
                  </dd>
                </div>
              </dl>

              {preflight.blockers.length > 0 ? (
                <p className="mt-3 text-xs leading-5 text-amber-100/80">Blocked by: {preflight.blockers.join(", ")}</p>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => runAction(action, true)}
                  disabled={running === action.id || !preflight.dryRunAllowed}
                  className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-sm font-bold text-cyan-100 transition hover:bg-cyan-300/20 disabled:opacity-50"
                >
                  {running === action.id ? "Validating…" : "Validate dry-run"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveActionId(activeActionId === action.id ? "" : action.id)
                    setError("")
                  }}
                  disabled={!hasProof || running === action.id}
                  className="rounded-2xl border border-emerald-300/30 bg-emerald-300/10 px-4 py-2 text-sm font-bold text-emerald-100 transition hover:bg-emerald-300/20 disabled:opacity-50"
                >
                  Open execution gate
                </button>
              </div>
              {action.nativeDryRun ? <p className="mt-3 text-xs text-cyan-100/80">This capability runs its native generator during dry-run validation.</p> : null}
            </div>
          )
        })}
      </div>

      {activeAction ? (
        <div className="mt-6 rounded-3xl border border-emerald-300/20 bg-emerald-300/10 p-5">
          <p className="text-sm font-black text-emerald-100">Execution gate: {activeAction.label}</p>
          <p className="mt-2 text-sm leading-6 text-emerald-100/70">
            Type <span className="font-mono font-bold text-emerald-50">{activeAction.confirmationText}</span> and add a maintenance reason. The proof is consumed by this one attempt.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-[0.8fr_1.2fr]">
            <input
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              placeholder={activeAction.confirmationText}
              className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none focus:border-emerald-200/60"
            />
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Maintenance reason (at least 8 characters)"
              className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none focus:border-emerald-200/60"
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => runAction(activeAction, false)}
              disabled={running === activeAction.id || !activeExecutionReady}
              className="rounded-2xl bg-emerald-300 px-4 py-2 text-sm font-black text-[#111629] disabled:opacity-50"
            >
              {running === activeAction.id ? "Executing…" : "Execute bounded refresh"}
            </button>
            {!activeExecutionReady ? <p className="self-center text-sm text-amber-100">Validate a current dry-run before executing.</p> : null}
          </div>
        </div>
      ) : null}

      {error ? <pre className="mt-6 whitespace-pre-wrap rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{error}</pre> : null}

      {result ? (
        <div className="mt-6 rounded-3xl border border-cyan-300/20 bg-cyan-300/10 p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-black text-cyan-100">{result.message}</p>
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-cyan-100">{result.status}</span>
          </div>
          <p className="mt-3 text-xs text-slate-400">Audit reference: {result.auditId}</p>
        </div>
      ) : null}
    </article>
  )
}
