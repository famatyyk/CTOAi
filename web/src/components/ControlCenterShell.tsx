"use client"

import { useMemo, useState } from "react"
import { controlCenterSnapshot } from "@/lib/controlCenterSnapshot"
import ControlCenterOpsGrid from "@/components/ControlCenterOpsGrid"
import ControlCenterDetailPanels from "@/components/ControlCenterDetailPanels"
import ControlCenterLiveProbe from "@/components/ControlCenterLiveProbe"
import ControlCenterChatPanel from "@/components/ControlCenterChatPanel"
import ControlCenterLegacyPanels from "@/components/ControlCenterLegacyPanels"
import ControlCenterActionPanel from "@/components/ControlCenterActionPanel"
import ControlCenterEvidencePanel from "@/components/ControlCenterEvidencePanel"
import { ControlCenterDataProvider } from "@/components/ControlCenterDataProvider"

const navSections = ["Overview", "Actions", "Codex Chat", "Local Status", "Evidence", "Docs Map"] as const

type ControlCenterTab = (typeof navSections)[number]

const actionItems = [
  "Wrap existing desktop_console as Windows EXE launcher.",
  "Keep web dashboard as the primary modern UI surface.",
  "Expose ctoa.ps1 actions through safe command tiles.",
  "Connect Codex/chat as the operator workspace.",
]

const timeline = [
  ["Cleaned local chaos", "CTOAi copies, worktrees, Downloads and cache cleanup."],
  ["Cleaned release noise", "Merged branches, workflow runs and old artifacts removed."],
  ["Recovered workspace", "Local cleanup and report hardening restored breathing room."],
  ["Starting Phase 1", "Control Center shell, names and module boundaries."],
]

function ToneOrb({ tone }: { tone: string }) {
  const toneClass =
    tone === "cyan"
      ? "from-cyan-300 to-sky-500"
      : tone === "pink"
        ? "from-fuchsia-400 to-pink-500"
        : "from-violet-400 to-indigo-500"

  return <span className={`h-3 w-3 rounded-full bg-gradient-to-br ${toneClass} shadow-[0_0_18px_rgba(34,211,238,0.55)]`} />
}

export default function ControlCenterShell() {
  return (
    <ControlCenterDataProvider>
      <ControlCenterShellContent />
    </ControlCenterDataProvider>
  )
}

function ControlCenterShellContent() {
  const [activeTab, setActiveTab] = useState<ControlCenterTab>("Overview")
  const subtitle = useMemo(() => {
    if (activeTab === "Overview") return "One place for Codex, local status, evidence and project boundaries."
    if (activeTab === "Actions") return "Safe local command tiles with dry-run and audit trail."
    if (activeTab === "Codex Chat") return "Operator workspace for guided work, chat handoff and future Codex integration."
    if (activeTab === "Local Status") return "File-backed status tiles for repo hygiene, release evidence, cost and audit."
    if (activeTab === "Evidence") return "Release evidence, repo hygiene, cost reporting and audit traces."
    return "Architecture boundaries, canonical repo schema and foundation cleanup."
  }, [activeTab])

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#111629] text-white">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -left-32 -top-44 h-[34rem] w-[34rem] rounded-full bg-fuchsia-400/25 blur-3xl" />
        <div className="absolute -bottom-40 right-0 h-[30rem] w-[30rem] rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,#313a5b_0%,transparent_35%),linear-gradient(135deg,rgba(255,255,255,0.03)_0%,transparent_40%)]" />
      </div>

      <section className="relative mx-auto flex min-h-screen w-full max-w-[1500px] items-start px-4 py-6 sm:px-8 lg:px-10">
        <div className="grid w-full overflow-hidden rounded-[2rem] border border-white/10 bg-[#0d1122]/95 shadow-[0_34px_110px_rgba(0,0,0,0.55)] backdrop-blur md:grid-cols-[260px_1fr]">
          <aside className="border-b border-white/10 bg-[#12172c] p-6 md:border-b-0 md:border-r">
            <div className="mb-10">
              <p className="text-xs uppercase tracking-[0.4em] text-cyan-200/70">CTOAi</p>
              <h1 className="mt-3 text-2xl font-black tracking-tight">Control Center</h1>
              <p className="mt-2 text-sm text-slate-400">Platform shell, launcher and operator cockpit.</p>
            </div>

            <nav className="space-y-2">
              {navSections.map((item) => (
                <button
                  key={item}
                  onClick={() => setActiveTab(item)}
                  className={`group flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm transition ${
                    item === activeTab
                      ? "bg-gradient-to-r from-fuchsia-500/70 to-violet-500/60 text-white shadow-[0_12px_30px_rgba(217,70,239,0.25)]"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <span>{item}</span>
                  <span className={`h-2 w-2 rounded-full ${item === activeTab ? "bg-cyan-200" : "bg-slate-700 group-hover:bg-slate-500"}`} />
                </button>
              ))}
            </nav>

            <div className="mt-10 rounded-3xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-fuchsia-200">Launcher</p>
              <p className="mt-3 text-sm text-slate-300">Windows EXE stays as the entry point. Web UI becomes the cockpit.</p>
              <button
                onClick={() => setActiveTab("Overview")}
                className="mt-5 w-full rounded-2xl bg-gradient-to-r from-cyan-300 to-fuchsia-400 px-4 py-3 text-sm font-black text-[#111629] shadow-[0_14px_40px_rgba(34,211,238,0.25)]"
              >
                Phase 1 shell
              </button>
            </div>
          </aside>

          <div className="min-h-0 p-5 sm:p-7 lg:p-10">
            <header className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-bold uppercase tracking-[0.32em] text-cyan-200">Operator cockpit</p>
                <h2 className="mt-3 max-w-4xl text-4xl font-black leading-tight tracking-[-0.04em] sm:text-5xl">{activeTab}</h2>
                <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-400">{subtitle}</p>
              </div>
              <div className="rounded-2xl border border-cyan-200/20 bg-cyan-200/10 px-5 py-4 text-sm text-cyan-100">
                <span className="block text-xs uppercase tracking-[0.24em] text-cyan-200/70">Mode</span>
                {controlCenterSnapshot.phase}
              </div>
            </header>

            <TabSwitchBar activeTab={activeTab} onChange={setActiveTab} />

            {activeTab === "Overview" ? <OverviewPanel onNavigate={setActiveTab} /> : null}
            {activeTab === "Actions" ? <ActionsPanel /> : null}
            {activeTab === "Codex Chat" ? <CodexPanel /> : null}
            {activeTab === "Local Status" ? <LocalStatusPanel /> : null}
            {activeTab === "Evidence" ? <EvidencePanel /> : null}
            {activeTab === "Docs Map" ? <DocsPanel /> : null}
          </div>
        </div>
      </section>
    </main>
  )
}

function OverviewPanel({ onNavigate }: { onNavigate: (tab: ControlCenterTab) => void }) {
  const resolveTargetTab = (label: string): ControlCenterTab => {
    return label === "Evidence pack" ? "Evidence" : "Local Status"
  }

  return (
    <>
      <div className="mb-5">
        <ControlCenterLiveProbe />
      </div>

      <section className="grid gap-5 lg:grid-cols-3">
        {controlCenterSnapshot.health.map((card) => (
          <button
            key={card.label}
            type="button"
            tabIndex={0}
            onClick={() => onNavigate(resolveTargetTab(card.label))}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault()
                onNavigate(resolveTargetTab(card.label))
              }
            }}
            className="relative cursor-pointer overflow-hidden rounded-3xl border border-white/10 bg-white/[0.06] p-6 text-left shadow-[0_18px_60px_rgba(0,0,0,0.25)] transition hover:-translate-y-0.5 hover:border-cyan-200/30 hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-cyan-200/60"
          >
            <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
            <div className="relative flex items-start justify-between">
              <div>
                <p className="text-sm font-bold text-slate-200">{card.label}</p>
                <p className="mt-6 text-5xl font-black tracking-[-0.06em]">
                  {card.value}
                  <span className="ml-2 text-lg font-semibold text-slate-300">{card.unit}</span>
                </p>
              </div>
              <ToneOrb tone={card.tone} />
            </div>
            <p className="relative mt-5 text-sm text-slate-400">{card.detail}</p>
            <p className="relative mt-5 text-xs uppercase tracking-[0.2em] text-cyan-100/70">
              Kliknij, aby przejść do {resolveTargetTab(card.label)}
            </p>
          </button>
        ))}
      </section>

      <section className="mt-5">
        <ControlCenterOpsGrid />
      </section>

      <section className="mt-5">
        <ControlCenterDetailPanels mode="all" />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.9fr]">
        <PlatformMap />
        <CodexDock />
      </section>

      <section className="mt-5">
        <TimelinePanel />
      </section>
    </>
  )
}

function TabSwitchBar({ activeTab, onChange }: { activeTab: ControlCenterTab; onChange: (tab: ControlCenterTab) => void }) {
  return (
    <div className="mb-6 grid gap-2 rounded-3xl border border-white/10 bg-white/[0.04] p-2 sm:grid-cols-3 lg:grid-cols-6">
      {navSections.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
            tab === activeTab
              ? "bg-cyan-300 text-[#111629] shadow-[0_10px_25px_rgba(34,211,238,0.22)]"
              : "text-slate-300 hover:bg-white/5 hover:text-white"
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}

function CodexPanel() {
  return (
    <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
      <ControlCenterChatPanel />
      <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
        <p className="text-sm font-black">Consolidation rule</p>
        <div className="mt-5 space-y-3">
          {[
            "This tab reuses the existing ChatWindow component and /api/chat route.",
            "We do not create another chat product here.",
            "The old standalone chat can stay as a focused page until Control Center fully replaces it.",
            "Next cleanup: one login, one chat engine, one operator console, one Windows launcher.",
          ].map((item) => (
            <p key={item} className="rounded-2xl bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
              {item}
            </p>
          ))}
        </div>
      </article>
    </section>
  )
}

function LocalStatusPanel() {
  return (
    <section className="space-y-5">
      <ControlCenterOpsGrid />
      <ControlCenterDetailPanels mode="all" />
    </section>
  )
}

function ActionsPanel() {
  return (
    <section className="space-y-5">
      <ControlCenterActionPanel target="local" />
    </section>
  )
}

function EvidencePanel() {
  return (
    <section className="space-y-5">
      <ControlCenterEvidencePanel />
      <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
        <p className="text-sm font-black">Why this matters</p>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Evidence and reporting are the bridge between the cockpit and release decisions: if the artifacts are missing, the dashboard should say so immediately.
        </p>
      </article>
    </section>
  )
}

function DocsPanel() {
  return (
    <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
      <PlatformMap />
      <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
        <p className="text-sm font-black">Docs source of truth</p>
        <div className="mt-5 rounded-3xl border border-amber-300/20 bg-amber-300/10 p-5">
          <p className="text-sm font-bold text-amber-100">REPO_SCHEMA.md has been refreshed.</p>
          <p className="mt-3 text-sm leading-6 text-amber-100/75">
            It now describes Control Center as the main cockpit, desktop as launcher and mobile console as backend/API plus legacy UI.
          </p>
        </div>
        <div className="mt-5 rounded-3xl border border-cyan-300/20 bg-cyan-300/10 p-5">
          <p className="text-sm font-bold text-cyan-100">Surface consolidation doc added.</p>
          <p className="mt-3 text-sm leading-6 text-cyan-100/75">
            Canonical target: one cockpit, one chat engine, one auth contract, one Windows launcher.
          </p>
        </div>
      </article>
      <FoundationCleanupPanel />
      <LegacyInventoryPanel />
      <CommandRiskPanel />
      <ControlCenterLegacyPanels />
    </section>
  )
}

function FoundationCleanupPanel() {
  const rows = [
    ["Main cockpit", "Control Center", "canonical"],
    ["Chat", "ChatWindow", "canonical"],
    ["Desktop console", "Windows launcher", "wrapper"],
    ["Mobile console", "Backend API", "backend-only"],
    ["Static dashboards", "Reference until absorbed", "legacy"],
    ["REPO_SCHEMA.md", "Canonical repo map", "refreshed"],
  ]

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6 xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Foundation cleanup map</p>
          <p className="mt-1 text-sm text-slate-400">Odgruzowanie fundamentu: one job, one canonical surface.</p>
        </div>
        <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-cyan-200">
          no new features
        </span>
      </div>

      <div className="mt-6 overflow-hidden rounded-3xl border border-white/10">
        <div className="grid grid-cols-[0.8fr_1fr_0.7fr] bg-white/[0.06] px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-400">
          <span>Area</span>
          <span>Target</span>
          <span>Decision</span>
        </div>
        {rows.map(([area, target, decision]) => (
          <div key={area} className="grid grid-cols-[0.8fr_1fr_0.7fr] border-t border-white/10 px-4 py-3 text-sm">
            <span className="font-semibold text-slate-100">{area}</span>
            <span className="text-slate-400">{target}</span>
            <span className="text-cyan-100">{decision}</span>
          </div>
        ))}
      </div>

      <p className="mt-5 text-sm leading-6 text-slate-400">
        Full cleanup inventory: docs/CTOAI_FOUNDATION_CLEANUP.md. Old surfaces are not deleted first; unique behavior is migrated into Control Center before anything gets retired.
      </p>
    </article>
  )
}

function LegacyInventoryPanel() {
  const rows = [
    ["Logs", "mobile_console /api/logs", "migrate"],
    ["Dashboard summary", "mobile_console /api/dashboard", "migrate"],
    ["Agent status", "mobile_console /api/agents/status", "migrate"],
    ["Command runner", "mobile_console /api/command", "guard"],
    ["User admin", "live dashboard /api/users", "migrate guarded"],
    ["Desktop updater", "desktop_console update_client", "keep in launcher"],
    ["Endpoint profiles", "desktop_console settings", "keep/wrap"],
    ["Bot scheduler/stats", "bot/dashboard app", "migrate"],
  ]

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6 xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Legacy feature inventory</p>
          <p className="mt-1 text-sm text-slate-400">What must move before old UI can be slimmed or retired.</p>
        </div>
        <span className="rounded-full bg-amber-300/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-amber-200">
          migrate before delete
        </span>
      </div>

      <div className="mt-6 overflow-hidden rounded-3xl border border-white/10">
        <div className="grid grid-cols-[0.8fr_1.1fr_0.7fr] bg-white/[0.06] px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-400">
          <span>Capability</span>
          <span>Current source</span>
          <span>Decision</span>
        </div>
        {rows.map(([capability, source, decision]) => (
          <div key={capability} className="grid grid-cols-[0.8fr_1.1fr_0.7fr] border-t border-white/10 px-4 py-3 text-sm">
            <span className="font-semibold text-slate-100">{capability}</span>
            <span className="text-slate-400">{source}</span>
            <span className="text-cyan-100">{decision}</span>
          </div>
        ))}
      </div>

      <p className="mt-5 text-sm leading-6 text-slate-400">
        Full checklist: docs/CTOAI_LEGACY_FEATURE_INVENTORY.md. This prevents accidental deletion of useful behavior hidden in old consoles.
      </p>
    </article>
  )
}

function CommandRiskPanel() {
  const rows = [
    ["read_only", "logs, status, metrics", "auto-refresh allowed"],
    ["safe_write", "preferences/profile save", "clear label"],
    ["guarded_write", "bot restart, one-click run", "confirmation + audit"],
    ["dangerous", "cleanup, user delete, rollback", "owner + typed confirmation"],
    ["forbidden_ui", "arbitrary shell/secrets", "do not render"],
  ]

  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6 xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Command risk model</p>
          <p className="mt-1 text-sm text-slate-400">Guardrails before legacy write actions become clickable.</p>
        </div>
        <span className="rounded-full bg-pink-300/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-pink-200">
          write actions blocked
        </span>
      </div>

      <div className="mt-6 overflow-hidden rounded-3xl border border-white/10">
        <div className="grid grid-cols-[0.7fr_1fr_1fr] bg-white/[0.06] px-4 py-3 text-xs uppercase tracking-[0.2em] text-slate-400">
          <span>Risk</span>
          <span>Examples</span>
          <span>UI behavior</span>
        </div>
        {rows.map(([risk, examples, behavior]) => (
          <div key={risk} className="grid grid-cols-[0.7fr_1fr_1fr] border-t border-white/10 px-4 py-3 text-sm">
            <span className="font-semibold text-slate-100">{risk}</span>
            <span className="text-slate-400">{examples}</span>
            <span className="text-cyan-100">{behavior}</span>
          </div>
        ))}
      </div>

      <p className="mt-5 text-sm leading-6 text-slate-400">
        Full model: docs/CTOAI_COMMAND_RISK_MODEL.md. Until this is implemented in code, `/api/command`, one-click execution, intel launch and user admin stay legacy/guarded.
      </p>
    </article>
  )
}

function PlatformMap() {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Platform boundary map</p>
          <p className="mt-1 text-sm text-slate-400">The body exists. Now we sharpen the names.</p>
        </div>
        <span className="rounded-full bg-fuchsia-400/15 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-fuchsia-200">
          CTOAi Platform
        </span>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {controlCenterSnapshot.lanes.map((lane) => (
          <div key={lane.title} className="rounded-3xl border border-white/10 bg-[#0e1327] p-5">
            <div className="flex items-center justify-between gap-4">
              <h3 className="font-black">{lane.title}</h3>
              <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-200">{lane.status}</span>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-400">{lane.copy}</p>
          </div>
        ))}
      </div>
    </article>
  )
}

function CodexDock() {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <p className="text-sm font-black">Codex chat dock</p>
      <div className="mt-5 rounded-3xl border border-cyan-300/20 bg-[#0c1328] p-5">
        <p className="text-xs uppercase tracking-[0.26em] text-cyan-200/70">Next integration</p>
        <h3 className="mt-3 text-2xl font-black tracking-tight">Bring the work conversation into the cockpit.</h3>
        <p className="mt-4 text-sm leading-6 text-slate-400">
          The current chat stays alive. Control Center becomes the place where chat, actions and system visibility sit together.
        </p>
      </div>

      <div className="mt-5 space-y-3">
        {actionItems.map((item) => (
          <div key={item} className="flex gap-3 rounded-2xl bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
            <span className="mt-1 h-2 w-2 rounded-full bg-cyan-300" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </article>
  )
}

function TimelinePanel() {
  return (
    <article className="rounded-3xl border border-white/10 bg-[#151b33] p-6">
      <p className="text-sm font-black">Recent cleanup trail</p>
      <div className="mt-6 space-y-4">
        {timeline.map(([title, copy]) => (
          <div key={title} className="grid grid-cols-[18px_1fr] gap-4">
            <div className="mt-1 h-full min-h-12 border-l border-cyan-300/30">
              <span className="-ml-[5px] block h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.65)]" />
            </div>
            <div>
              <p className="font-bold">{title}</p>
              <p className="mt-1 text-sm text-slate-400">{copy}</p>
            </div>
          </div>
        ))}
      </div>
    </article>
  )
}
