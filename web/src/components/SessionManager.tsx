"use client"
import { useState, useEffect } from "react"
import { MessageSquare, Plus, Trash2 } from "lucide-react"

export interface Session {
  id: string
  title: string
  createdAt: number
  messages: { role: "user" | "assistant"; content: string }[]
}

interface Props {
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  sessions: Session[]
  onDelete: (id: string) => void
}

export default function SessionManager({ activeId, onSelect, onNew, sessions, onDelete }: Props) {
  return (
    <aside className="w-64 border-r border-border flex flex-col bg-panel shrink-0">
      <div className="px-4 py-5 border-b border-border">
        <h1 className="text-white font-semibold tracking-tight">CTOAi</h1>
        <p className="text-xs text-zinc-500 mt-0.5">AI Operations Platform</p>
      </div>
      <div className="px-2 py-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:border-accent text-sm text-zinc-400 hover:text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nowa sesja
        </button>
      </div>
      <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
        {sessions.map(s => (
          <div key={s.id} className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${s.id === activeId ? "bg-accent/20 text-white" : "text-zinc-400 hover:bg-white/5 hover:text-white"}`}>
            <MessageSquare className="w-4 h-4 shrink-0" onClick={() => onSelect(s.id)} />
            <span className="flex-1 truncate" onClick={() => onSelect(s.id)}>{s.title}</span>
            {sessions.length > 1 && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(s.id) }}
                className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-border">
        <p className="text-xs text-zinc-600">Qwen2.5-Coder 1.5B</p>
      </div>
    </aside>
  )
}