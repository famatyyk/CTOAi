"use client"

import { useMemo, useState, type ComponentType } from "react"
import { Shield, Users, Wrench, Crown, LogIn, UserPlus } from "lucide-react"

export type AccountRole = "owner" | "operator" | "member"

export interface AuthUser {
  username: string
  displayName: string
  role: AccountRole
  joinedAt: number
}

interface LoginPanelProps {
  onLogin: (payload: { username: string; password: string; role: AccountRole; mode: "login" | "register" }) => Promise<void>
}

const ROLE_META: Record<AccountRole, { label: string; icon: ComponentType<{ className?: string }>; hint: string }> = {
  owner: { label: "Owner", icon: Crown, hint: "Strategic control, policy decisions, release approvals." },
  operator: { label: "Operator", icon: Wrench, hint: "Daily operations, quality checks, workflow execution." },
  member: { label: "Member", icon: Users, hint: "Community participation, ideation, and feedback loops." },
}

export default function LoginPanel({ onLogin }: LoginPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<AccountRole>("member")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const roleInfo = useMemo(() => ROLE_META[role], [role])
  const RoleIcon = roleInfo.icon

  async function submit() {
    const login = username.trim().toLowerCase()
    const pass = password.trim()

    if (!login || !pass) {
      setError("Username and password are required.")
      return
    }

    setError("")
    setLoading(true)
    try {
      await onLogin({ username: login, password: pass, role, mode })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Authentication failed"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 text-white px-6 py-10 flex items-center justify-center">
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-6">
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300">
            <Shield className="w-3 h-3" />
            Beast Mode Access
          </div>
          <h1 className="text-3xl font-semibold mt-4">CTOAi Identity Gateway</h1>
          <p className="text-zinc-400 mt-2 text-sm">Login is now backed by server-side JWT + RBAC.</p>

          <div className="mt-6 space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`rounded-lg px-3 py-2 text-sm border ${mode === "login" ? "border-emerald-500 bg-emerald-500/10" : "border-zinc-800 bg-zinc-950"}`}
              >
                <LogIn className="w-4 h-4 inline mr-2" />Login
              </button>
              <button
                type="button"
                onClick={() => setMode("register")}
                className={`rounded-lg px-3 py-2 text-sm border ${mode === "register" ? "border-emerald-500 bg-emerald-500/10" : "border-zinc-800 bg-zinc-950"}`}
              >
                <UserPlus className="w-4 h-4 inline mr-2" />Register
              </button>
            </div>

            <label className="block">
              <span className="text-xs text-zinc-400">Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                placeholder="famatyyk"
              />
            </label>

            <label className="block">
              <span className="text-xs text-zinc-400">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                placeholder="********"
              />
            </label>

            {mode === "register" && (
              <div>
                <span className="text-xs text-zinc-400">Initial account type</span>
                <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {(Object.keys(ROLE_META) as AccountRole[]).map((r) => {
                    const Icon = ROLE_META[r].icon
                    const active = role === r
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setRole(r)}
                        className={
                          "rounded-lg border px-3 py-2 text-left transition " +
                          (active
                            ? "border-emerald-500 bg-emerald-500/10"
                            : "border-zinc-800 bg-zinc-950 hover:border-zinc-700")
                        }
                      >
                        <div className="flex items-center gap-2 text-sm">
                          <Icon className="w-4 h-4" />
                          {ROLE_META[r].label}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {error && <p className="text-xs text-rose-400">{error}</p>}

            <button
              type="button"
              onClick={submit}
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-zinc-950 font-medium px-4 py-2"
            >
              {mode === "login" ? <LogIn className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
              {loading ? "Please wait..." : mode === "login" ? "Enter command layer" : "Create account"}
            </button>

            <p className="text-xs text-zinc-500">
              Seed accounts: famatyyk / ctoa-owner, strategos / ctoa-ops, recruit / ctoa-community
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <h2 className="text-lg font-medium">Role briefing</h2>
          <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <RoleIcon className="w-4 h-4 text-emerald-400" />
              {roleInfo.label}
            </div>
            <p className="text-sm text-zinc-400 mt-2">{roleInfo.hint}</p>
          </div>

          <div className="mt-5 space-y-3 text-sm text-zinc-400">
            <p>Profiles are stored server-side with bcrypt password hashing.</p>
            <p>Invites, role management, and community feed are now backed by API.</p>
            <p>Chat requests require valid JWT when auth is enabled.</p>
          </div>
        </section>
      </div>
    </div>
  )
}
