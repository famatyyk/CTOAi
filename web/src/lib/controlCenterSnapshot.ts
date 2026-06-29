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
  generatedAt: "2026-06-29",
  phase: "Phase 1-3 shell",
  backend: {
    apiUrl: "configured at runtime",
    reachable: null,
    summary: "Live backend probe is added by /api/control-center.",
  },
  health: [
    {
      label: "VPS free space",
      value: "8.9",
      unit: "GB",
      detail: "Last known after Docker cleanup",
      tone: "cyan",
    },
    {
      label: "Root disk usage",
      value: "76",
      unit: "%",
      detail: "Recovered from 100% full",
      tone: "violet",
    },
    {
      label: "GitHub artifacts",
      value: "2008",
      unit: "left",
      detail: "Down from 4262",
      tone: "pink",
    },
  ],
  lanes: [
    {
      title: "Control Center",
      status: "Phase 1",
      copy: "Single launcher and visual command surface for local, VPS, GitHub, bot and Codex work.",
    },
    {
      title: "Runtime Plane",
      status: "Live",
      copy: "Bot runtime, Xvfb startup, input backend, scheduler window and deployable Docker image.",
    },
    {
      title: "Ops Plane",
      status: "Recovered",
      copy: "VPS, Docker, disk pressure, rebuilds, deploy commands and service health.",
    },
    {
      title: "Governance Plane",
      status: "Needs map",
      copy: "Approvals, evidence, CI gates, security rules and decision history.",
    },
  ],
  actions: [
    {
      label: "VPS health audit",
      risk: "read-only",
      source: "ctoa.ps1 vps",
    },
    {
      label: "Docker image report",
      risk: "read-only",
      source: "ssh docker system df",
    },
    {
      label: "Bot runtime logs",
      risk: "read-only",
      source: "docker compose logs infra-bot",
    },
    {
      label: "GitHub CI summary",
      risk: "read-only",
      source: "gh run list",
    },
  ],
}
