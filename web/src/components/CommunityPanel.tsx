"use client"

import { useEffect, useState } from "react"

interface CommunityMember {
  username: string
  display_name: string
  role: "owner" | "operator" | "member"
  created_at: string
}

interface CommunityEvent {
  id: string
  type: string
  actor: string
  target: string
  at: string
  meta?: Record<string, unknown>
}

interface CommunityPanelProps {
  role: "owner" | "operator" | "member"
  onCommunityCount: (count: number) => void
}

const ROLE_OPTIONS = ["owner", "operator", "member"] as const

export default function CommunityPanel({ role, onCommunityCount }: CommunityPanelProps) {
  const [members, setMembers] = useState<CommunityMember[]>([])
  const [feed, setFeed] = useState<CommunityEvent[]>([])
  const [inviteUser, setInviteUser] = useState("")
  const [inviteRole, setInviteRole] = useState<(typeof ROLE_OPTIONS)[number]>("member")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  const canInvite = role === "owner" || role === "operator"
  const canSetRole = role === "owner"

  async function refresh() {
    setError("")
    const [membersRes, feedRes] = await Promise.all([
      fetch("/api/auth?path=members", { cache: "no-store" }),
      fetch("/api/auth?path=feed", { cache: "no-store" }),
    ])

    const membersData = await membersRes.json()
    const feedData = await feedRes.json()

    if (!membersRes.ok) {
      setError(membersData?.detail || membersData?.error || "Failed to load members")
      return
    }

    setMembers(membersData.members || [])
    onCommunityCount((membersData.members || []).length)
    setFeed(feedData.events || [])
  }

  useEffect(() => {
    refresh().catch(() => setError("Failed to load community data"))
  }, [])

  async function createInvite() {
    if (!inviteUser.trim()) {
      setError("Username is required")
      return
    }
    setError("")
    setMessage("")

    const r = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "invite", payload: { username: inviteUser, role: inviteRole } }),
    })

    const data = await r.json()
    if (!r.ok) {
      setError(data?.detail || data?.error || "Invite failed")
      return
    }

    setMessage(`Invite code: ${data.invite.code}`)
    setInviteUser("")
    await refresh()
  }

  async function changeRole(username: string, nextRole: (typeof ROLE_OPTIONS)[number]) {
    setError("")
    setMessage("")
    const r = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "setRole", payload: { username, role: nextRole } }),
    })
    const data = await r.json()
    if (!r.ok) {
      setError(data?.detail || data?.error || "Role update failed")
      return
    }
    setMessage(`Updated ${data.member.username} -> ${data.member.role}`)
    await refresh()
  }

  return (
    <section className="border-t border-border px-4 py-4 bg-zinc-950/50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-white">Community Control</h3>
        <span className="text-xs text-zinc-400">{members.length} members</span>
      </div>

      {canInvite && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
          <input
            value={inviteUser}
            onChange={(e) => setInviteUser(e.target.value)}
            placeholder="username"
            className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs outline-none focus:border-emerald-500"
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as (typeof ROLE_OPTIONS)[number])}
            className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs outline-none focus:border-emerald-500"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={createInvite}
            className="rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-xs font-medium px-3 py-2"
          >
            Create invite
          </button>
          <button
            type="button"
            onClick={() => refresh()}
            className="rounded-lg border border-zinc-700 hover:border-zinc-500 text-zinc-300 text-xs px-3 py-2"
          >
            Refresh
          </button>
        </div>
      )}

      {message && <p className="text-xs text-emerald-400 mb-2">{message}</p>}
      {error && <p className="text-xs text-rose-400 mb-2">{error}</p>}

      <div className="grid lg:grid-cols-2 gap-3">
        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <div className="bg-zinc-900 px-3 py-2 text-xs text-zinc-400">Profiles & roles</div>
          <div className="max-h-44 overflow-y-auto">
            {members.map((m) => (
              <div key={m.username} className="px-3 py-2 border-t border-zinc-900 text-xs flex items-center gap-2">
                <span className="text-zinc-300 flex-1">@{m.username}</span>
                <span className="text-zinc-500">{m.role}</span>
                {canSetRole && (
                  <select
                    value={m.role}
                    onChange={(e) => changeRole(m.username, e.target.value as (typeof ROLE_OPTIONS)[number])}
                    className="rounded border border-zinc-700 bg-zinc-900 text-zinc-300 px-1 py-0.5"
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <div className="bg-zinc-900 px-3 py-2 text-xs text-zinc-400">Activity feed</div>
          <div className="max-h-44 overflow-y-auto">
            {feed.map((e) => (
              <div key={e.id} className="px-3 py-2 border-t border-zinc-900 text-xs">
                <p className="text-zinc-300">{e.type} - @{e.actor} - {e.target}</p>
                <p className="text-zinc-500">{new Date(e.at).toLocaleString()}</p>
              </div>
            ))}
            {feed.length === 0 && <p className="px-3 py-2 text-xs text-zinc-500">No activity yet.</p>}
          </div>
        </div>
      </div>
    </section>
  )
}
