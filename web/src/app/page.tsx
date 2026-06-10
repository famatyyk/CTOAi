"use client"
import { useState, useEffect, useCallback } from "react"
import ChatWindow from "@/components/ChatWindow"
import StatusBar from "@/components/StatusBar"
import SessionManager, { Session } from "@/components/SessionManager"

function makeId() { return Date.now().toString(36) + Math.random().toString(36).slice(2) }
function newSession(): Session { return { id: makeId(), title: "Nowa rozmowa", createdAt: Date.now(), messages: [] } }
const STORAGE_KEY = "ctoa_sessions"
const ACTIVE_KEY = "ctoa_active_session"

function loadSessions(): Session[] {
  if (typeof window === "undefined") return []
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") } catch { return [] }
}

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string>("")
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let s = loadSessions()
    const savedActive = localStorage.getItem(ACTIVE_KEY)
    if (s.length === 0) { const fresh = newSession(); s = [fresh] }
    setSessions(s)
    const active = s.find(x => x.id === savedActive) ? savedActive! : s[0].id
    setActiveId(active)
    setReady(true)
  }, [])

  const saveSessions = useCallback((s: Session[]) => {
    setSessions(s)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  }, [])

  const handleNew = useCallback(() => {
    const s = newSession()
    const updated = [s, ...sessions]
    saveSessions(updated)
    setActiveId(s.id)
    localStorage.setItem(ACTIVE_KEY, s.id)
  }, [sessions, saveSessions])

  const handleSelect = useCallback((id: string) => {
    setActiveId(id)
    localStorage.setItem(ACTIVE_KEY, id)
  }, [])

  const handleDelete = useCallback((id: string) => {
    const updated = sessions.filter(s => s.id !== id)
    if (updated.length === 0) { const fresh = newSession(); saveSessions([fresh]); setActiveId(fresh.id); return }
    saveSessions(updated)
    if (activeId === id) { setActiveId(updated[0].id); localStorage.setItem(ACTIVE_KEY, updated[0].id) }
  }, [sessions, activeId, saveSessions])

  const handleMessagesChange = useCallback((id: string, messages: Session["messages"]) => {
    setSessions(prev => {
      const updated = prev.map(s => {
        if (s.id !== id) return s
        const title = messages.find(m => m.role === "user")?.content.slice(0, 40) || "Nowa rozmowa"
        return { ...s, messages, title }
      })
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      return updated
    })
  }, [])

  const activeSession = sessions.find(s => s.id === activeId)

  if (!ready) return <div className="flex h-screen bg-surface" />

  return (
    <div className="flex h-screen bg-surface">
      <SessionManager
        activeId={activeId}
        sessions={sessions}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
      />
      <main className="flex-1 flex flex-col min-w-0">
        <StatusBar />
        <ChatWindow
          key={activeId}
          sessionId={activeId}
          initialMessages={activeSession?.messages || []}
          onMessagesChange={(msgs) => handleMessagesChange(activeId, msgs)}
        />
      </main>
    </div>
  )
}