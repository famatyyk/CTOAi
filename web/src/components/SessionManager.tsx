"use client"

import { useState, useEffect } from "react"
import { MessageSquare, Plus, Trash2, LogOut, Users } from "lucide-react"
import { AuthUser } from "@/components/LoginPanel"

export interface Session {
  id: string
  title: string
  createdAt: number
  messages: { role: "user" | "assistant"; content: string }[]
}

interface Props {
  user: AuthUser
  communityCount: number
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  sessions: Session[]
  onDelete: (id: string) => void
  onLogout: () => void
}

const ROLE_LABEL: Record<AuthUser["role"], string> = {
  owner: "Owner",
  operator: "Operator",
  member: "Member",
}

export default function SessionManager({
  user,
  communityCount,
  activeId,
  onSelect,
  onNew,
  sessions,
  onDelete,
  onLogout,
}: Props) {
  const [modelLabel, setModelLabel] = useState<string>("...")

  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then((d) => {
        if (d?.model) setModelLabel(d.model)
      })
      .catch(() => setModelLabel("offline"))
  }, [])

  return (
    <aside className="w-72 border-r border-border flex flex-col bg-panel shrink-0">
      <div className="px-4 py-5 border-b border-border">
        <h1 className="text-white font-semibold tracking-tight">CTOAi</h1>
        <p className="text-xs text-zinc-500 mt-0.5">AI Operations Platform</p>
      </div>

      <div className="px-4 py-3 border-b border-border space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-500">Signed in</span>
          <span className="rounded-full border border-emerald-500/50 px-2 py-0.5 text-emerald-300">{ROLE_LABEL[user.role]}</span>
        </div>
        <p className="text-sm text-white truncate">@{user.username}</p>
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span className="inline-flex items-center gap-1"><Users className="w-3 h-3" />Community</span>
          <span>{communityCount} members</span>
        </div>
        <button
          onClick={onLogout}
          className="w-full mt-1 inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>

      <div className="px-2 py-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-accent text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          New session
        </button>
      </div>

      <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
              s.id === activeId ? "bg-accent/20 text-white" : "text-zinc-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <MessageSquare className="w-4 h-4 shrink-0" onClick={() => onSelect(s.id)} />
            <span className="flex-1 truncate" onClick={() => onSelect(s.id)}>
              {s.title}
            </span>
            {sessions.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(s.id)
                }}
                className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border">
        <p className="text-xs text-zinc-600">{modelLabel}</p>
      </div>
    </aside>
  )
}
