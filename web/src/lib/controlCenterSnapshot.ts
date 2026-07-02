export type ControlCenterSnapshot = {
  generatedAt: string
  phase: string
  backend: {
    apiUrl: string
    reachable: boolean | null
    summary: string
    status?: unknown
  }
  health: Array<{
    label: string
    value: string
    unit: string
    detail: string
    tone: "cyan" | "violet" | "pink"
  }>
  lanes: Array<{
    title: string
    status: string
    copy: string
  }>
  actions: Array<{
    label: string
    risk: "read-only" | "guarded-write"
    source: string
  }>
}

export const controlCenterSnapshot: ControlCenterSnapshot = {
  generatedAt: "runtime",
  phase: "Live control surface",
  backend: {
    apiUrl: "configured at runtime",
    reachable: null,
    summary: "Live backend probe is served by /api/control-center.",
  },
  health: [
    {
      label: "Backend probe",
      value: "live",
      unit: "status",
      detail: "The control-center route checks backend reachability before rendering details.",
      tone: "cyan",
    },
    {
      label: "Ops panels",
      value: "live",
      unit: "status",
      detail: "Repo hygiene, release evidence, cost and audit panels load from local files.",
      tone: "violet",
    },
    {
      label: "Evidence pack",
      value: "file-backed",
      unit: "state",
      detail: "Evidence and report links resolve from the current runtime config.",
      tone: "pink",
    },
  ],
  lanes: [
    {
      title: "Control Center",
      status: "Live",
      copy: "Single launcher and visual command surface for local evidence, chat and Codex work.",
    },
    {
      title: "Runtime Plane",
      status: "Live",
      copy: "Local runtime, input backend, scheduler window and deployable tooling.",
    },
    {
      title: "Ops Plane",
      status: "Live",
      copy: "Workspace hygiene, local evidence, report refreshes and service health.",
    },
    {
      title: "Governance Plane",
      status: "Guarded",
      copy: "Approvals, evidence, CI gates, reporting, security rules and decision history.",
    },
  ],
  actions: [
    {
      label: "Workspace hygiene audit",
      risk: "read-only",
      source: "Control Center action: repo-hygiene-refresh",
    },
    {
      label: "API cost report",
      risk: "read-only",
      source: "Control Center action: api-cost-refresh",
    },
    {
      label: "Evidence pack",
      risk: "read-only",
      source: "Control Center action: evidence-pack-refresh",
    },
  ],
}
