"use client"

import { useEffect, useMemo, useState } from "react"
import type { ControlCenterAction, ControlCenterActionResult } from "@/lib/controlCenterActions"
import type { ControlCenterViewer, ControlCenterAuthStatus } from "@/lib/controlCenterAuth"
import { canRunControlCenterAction } from "@/lib/controlCenterPolicy"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

type ActionLoadState =
  | { state: "loading"; actions: ControlCenterAction[]; viewer: ControlCenterViewer | null; authStatus: ControlCenterAuthStatus; error: null }
  | { state: "ready"; actions: ControlCenterAction[]; viewer: ControlCenterViewer | null; authStatus: ControlCenterAuthStatus; error: null }
  | { state: "error"; actions: ControlCenterAction[]; viewer: null; authStatus: "unavailable"; error: string }

const riskTone: Record<ControlCenterAction["riskClass"], string> = {
  read_only: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
  safe_write: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
  guarded_write: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  dangerous: "border-pink-300/30 bg-pink-300/10 text-pink-100",
  forbidden_ui: "border-slate-300/20 bg-slate-300/10 text-slate-300",
}

export default function ControlCenterActionPanel({ target }: { target?: ControlCenterAction["target"] }) {
  const [loadState, setLoadState] = useState<ActionLoadState>({
    state: "loading",
    actions: [],
    viewer: null,
    authStatus: "unauthenticated",
    error: null,
  })
  const [activeActionId, setActiveActionId] = useState<string>("")
  const [confirmation, setConfirmation] = useState("")
  const [reason, setReason] = useState("")
  const [running, setRunning] = useState<string>("")
  const [result, setResult] = useState<ControlCenterActionResult | null>(null)
  const [error, setError] = useState<string>("")
  const [refreshTick, setRefreshTick] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function loadActions() {
      try {
        const response = await fetchWithTimeout("/api/control-center/actions", { cache: "no-store" }, 5000)
        const data = (await response.json()) as {
          actions: ControlCenterAction[]
          viewer: ControlCenterViewer | null
          authStatus: ControlCenterAuthStatus
        }
        if (!cancelled) {
          setLoadState({
            state: "ready",
            actions: data.actions || [],
            viewer: data.viewer || null,
            authStatus: data.authStatus || "unauthenticated",
            error: null,
          })
        }
      } catch (loadError) {
        if (!cancelled) {
          setLoadState({
            state: "error",
            actions: [],
            viewer: null,
            authStatus: "unavailable",
            error: loadError instanceof Error ? loadError.message : "Action catalog failed to load.",
          })
        }
      }
    }

    loadActions()
    return () => {
      cancelled = true
    }
  }, [refreshTick])

  const actions = useMemo(
    () => loadState.actions.filter((action) => !target || action.target === target),
    [loadState.actions, target],
  )
  const viewer = loadState.state === "error" ? null : loadState.viewer
  const viewerRole = viewer?.role || null
  const authReady = viewer !== null
  const authStatus = loadState.state === "error" ? "unavailable" : loadState.authStatus
  const visibleActions = useMemo(() => {
    if (!viewerRole) return []
    return actions.filter((action) => canRunControlCenterAction(action, viewerRole).allowed)
  }, [actions, viewerRole])
  const hiddenActionCount = actions.length - visibleActions.length
  const activeAction = visibleActions.find((action) => action.id === activeActionId) || null

  function actionGate(action: ControlCenterAction) {
    return canRunControlCenterAction(action, viewerRole)
  }

  async function runAction(action: ControlCenterAction, dryRun: boolean) {
    setRunning(action.id)
    setError("")
    setResult(null)

    try {
      const response = await fetch("/api/control-center/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          actionId: action.id,
          confirmation,
          reason,
          dryRun,
        }),
      })
      const data = (await response.json()) as { ok: boolean; error?: string; result?: ControlCenterActionResult }
      if (!response.ok || !data.result) {
        throw new Error(data.error || "Action failed.")
      }
      setResult(data.result)
      setConfirmation("")
      setReason("")
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Action failed.")
    } finally {
      setRunning("")
    }
  }

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-black">Local action panel</p>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
            Fixed allowlisted local commands only. Read-only actions refresh file-backed reports; guarded writes require confirmation and an audit reason.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
            {loadState.state === "loading" ? "loading" : `${visibleActions.length} actions`}
          </span>
          <button
            type="button"
            onClick={() => setRefreshTick((value) => value + 1)}
            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            Refresh auth
          </button>
        </div>
      </div>

      {loadState.state === "error" ? (
        <div className="mt-5 rounded-3xl border border-pink-300/20 bg-pink-300/10 p-4 text-sm text-pink-100">{loadState.error}</div>
      ) : null}

      {hiddenActionCount > 0 ? (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
          {hiddenActionCount} action{hiddenActionCount > 1 ? "s" : ""} hidden for your role.
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {visibleActions.map((action) => (
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

            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Minimum role: {action.minimumRole}</p>

            <p className="mt-4 rounded-2xl bg-black/20 px-4 py-3 font-mono text-xs leading-5 text-slate-400">
              {action.commandSummary}
            </p>

            {action.riskClass === "guarded_write" || action.riskClass === "dangerous" ? (
              <button
                type="button"
                onClick={() => {
                  setActiveActionId(activeActionId === action.id ? "" : action.id)
                  setError("")
                  setResult(null)
                }}
                disabled={!actionGate(action).allowed}
                className="mt-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-sm font-bold text-amber-100 transition hover:bg-amber-300/20"
              >
                {activeActionId === action.id ? "Hide confirmation" : actionGate(action).allowed ? "Open confirmation gate" : "Operator sign-in required"}
              </button>
            ) : (
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => runAction(action, false)}
                  disabled={running === action.id || !actionGate(action).allowed}
                  className="rounded-2xl bg-cyan-300 px-4 py-2 text-sm font-black text-[#111629] disabled:opacity-50"
                >
                  {running === action.id ? "Running..." : actionGate(action).allowed ? "Run now" : "Sign in"}
                </button>
                <button
                  type="button"
                  onClick={() => runAction(action, true)}
                  disabled={running === action.id || !actionGate(action).allowed}
                  className="rounded-2xl border border-white/10 px-4 py-2 text-sm font-bold text-slate-300 transition hover:bg-white/10 disabled:opacity-50"
                >
                  {actionGate(action).allowed ? "Dry run" : "Sign in"}
                </button>
              </div>
            )}
            {!actionGate(action).allowed ? <p className="mt-3 text-sm text-amber-100/70">{actionGate(action).reason}</p> : null}
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
        {authReady ? (
          <>
            Signed in as <span className="font-semibold text-white">{viewer?.displayName}</span> · role{" "}
            <span className="font-semibold text-cyan-100">{viewer?.role}</span>
          </>
        ) : (
          <>
            {authStatus === "unavailable"
              ? "Auth status unavailable."
              : "Sign in to enable Control Center actions. Local seed-login requires explicit development-only env configuration."}
          </>
        )}
      </div>

      {activeAction ? (
        <div className="mt-6 rounded-3xl border border-amber-300/20 bg-amber-300/10 p-5">
          <p className="text-sm font-black text-amber-100">Confirmation required: {activeAction.label}</p>
          <p className="mt-2 text-sm leading-6 text-amber-100/70">
            Type <span className="font-mono font-bold text-amber-50">{activeAction.confirmationText}</span> and add a maintenance reason.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-[0.8fr_1.2fr]">
            <input
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              placeholder={activeAction.confirmationText}
              className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none focus:border-amber-200/60"
            />
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Reason, e.g. restart after deploy verification"
              className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none focus:border-amber-200/60"
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => runAction(activeAction, true)}
              disabled={running === activeAction.id || !actionGate(activeAction).allowed}
              className="rounded-2xl border border-amber-300/30 px-4 py-2 text-sm font-bold text-amber-100 transition hover:bg-amber-300/20 disabled:opacity-50"
            >
              {actionGate(activeAction).allowed ? "Dry run local action" : "Sign in"}
            </button>
            <button
              type="button"
              onClick={() => runAction(activeAction, false)}
              disabled={running === activeAction.id || !actionGate(activeAction).allowed}
              className="rounded-2xl bg-amber-300 px-4 py-2 text-sm font-black text-[#111629] disabled:opacity-50"
            >
              {running === activeAction.id ? "Running..." : actionGate(activeAction).allowed ? "Execute local action" : "Operator sign-in required"}
            </button>
          </div>
          {!actionGate(activeAction).allowed ? <p className="mt-3 text-sm text-amber-100/70">{actionGate(activeAction).reason}</p> : null}
        </div>
      ) : null}

      {error ? <pre className="mt-6 whitespace-pre-wrap rounded-3xl border border-pink-300/20 bg-pink-300/10 p-5 text-sm text-pink-100">{error}</pre> : null}

      {result ? (
        <div className="mt-6 rounded-3xl border border-cyan-300/20 bg-cyan-300/10 p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-black text-cyan-100">
              {result.ok ? "Action completed" : "Action failed"} · {result.auditId}
            </p>
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-cyan-100">{result.dryRun ? "dry-run" : "executed"}</span>
          </div>
          <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl bg-[#090e1d] p-4 text-xs leading-6 text-slate-300">
            {result.output}
          </pre>
        </div>
      ) : null}
    </article>
  )
}
