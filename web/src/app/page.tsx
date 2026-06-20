"use client"

import { useState, useEffect, useCallback } from "react"
import ChatWindow from "@/components/ChatWindow"
import StatusBar from "@/components/StatusBar"
import SessionManager, { Session } from "@/components/SessionManager"
import LoginPanel, { AuthUser } from "@/components/LoginPanel"
import CommunityPanel from "@/components/CommunityPanel"

function makeId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

function newSession(): Session {
  return { id: makeId(), title: "Nowa rozmowa", createdAt: Date.now(), messages: [] }
}

const ACTIVE_KEY = "ctoa_active_session"

function loadSessions(user: string): Session[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem(`ctoa_sessions_${user}`) || "[]")
  } catch {
    return []
  }
}

export default function Home() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string>("")
  const [communityCount, setCommunityCount] = useState(0)
  const [ready, setReady] = useState(false)

  const refreshAuth = useCallback(async () => {
    const r = await fetch("/api/auth?path=me", { cache: "no-store" })
    if (!r.ok) {
      setAuthUser(null)
      return
    }
    const data = await r.json()
    if (data?.user) {
      setAuthUser({
        username: data.user.username,
        displayName: data.user.display_name || data.user.username,
        role: data.user.role,
        joinedAt: Date.now(),
      })
    }
  }, [])

  useEffect(() => {
    refreshAuth().finally(() => setReady(true))
  }, [refreshAuth])

  useEffect(() => {
    if (!authUser) {
      setSessions([])
      setActiveId("")
      return
    }
    let s = loadSessions(authUser.username)
    const savedActive = localStorage.getItem(`${ACTIVE_KEY}_${authUser.username}`)
    if (s.length === 0) {
      const fresh = newSession()
      s = [fresh]
      localStorage.setItem(`ctoa_sessions_${authUser.username}`, JSON.stringify(s))
    }
    setSessions(s)
    const active = s.find((x) => x.id === savedActive) ? savedActive! : s[0].id
    setActiveId(active)
    localStorage.setItem(`${ACTIVE_KEY}_${authUser.username}`, active)
  }, [authUser])

  const saveSessions = useCallback(
    (nextSessions: Session[]) => {
      if (!authUser) return
      setSessions(nextSessions)
      localStorage.setItem(`ctoa_sessions_${authUser.username}`, JSON.stringify(nextSessions))
    },
    [authUser],
  )

  const handleLogin = useCallback(async (payload: { username: string; password: string; role: AuthUser["role"]; mode: "login" | "register" }) => {
    const action = payload.mode
    const body =
      payload.mode === "register"
        ? { username: payload.username, password: payload.password, role: "member" }
        : { username: payload.username, password: payload.password }

    const r = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, payload: body }),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data?.detail || data?.error || "Auth failed")
    setAuthUser({
      username: data.user.username,
      displayName: data.user.display_name || data.user.username,
      role: data.user.role,
      joinedAt: Date.now(),
    })
  }, [])

  const handleLogout = useCallback(async () => {
    await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "logout" }),
    })
    setAuthUser(null)
  }, [])

  const handleNew = useCallback(() => {
    const s = newSession()
    const updated = [s, ...sessions]
    saveSessions(updated)
    setActiveId(s.id)
    if (authUser) {
      localStorage.setItem(`${ACTIVE_KEY}_${authUser.username}`, s.id)
    }
  }, [sessions, saveSessions, authUser])

  const handleSelect = useCallback(
    (id: string) => {
      setActiveId(id)
      if (authUser) {
        localStorage.setItem(`${ACTIVE_KEY}_${authUser.username}`, id)
      }
    },
    [authUser],
  )

  const handleDelete = useCallback(
    (id: string) => {
      const updated = sessions.filter((s) => s.id !== id)
      if (updated.length === 0) {
        const fresh = newSession()
        saveSessions([fresh])
        setActiveId(fresh.id)
        if (authUser) {
          localStorage.setItem(`${ACTIVE_KEY}_${authUser.username}`, fresh.id)
        }
        return
      }
      saveSessions(updated)
      if (activeId === id) {
        setActiveId(updated[0].id)
        if (authUser) {
          localStorage.setItem(`${ACTIVE_KEY}_${authUser.username}`, updated[0].id)
        }
      }
    },
    [sessions, activeId, saveSessions, authUser],
  )

  const handleMessagesChange = useCallback(
    (id: string, messages: Session["messages"]) => {
      if (!authUser) return
      setSessions((prev) => {
        const updated = prev.map((s) => {
          if (s.id !== id) return s
          const title = messages.find((m) => m.role === "user")?.content.slice(0, 40) || "Nowa rozmowa"
          return { ...s, messages, title }
        })
        localStorage.setItem(`ctoa_sessions_${authUser.username}`, JSON.stringify(updated))
        return updated
      })
    },
    [authUser],
  )

  const activeSession = sessions.find((s) => s.id === activeId)

  if (!ready) {
    return <div className="flex h-screen bg-surface" />
  }

  if (!authUser) {
    return <LoginPanel onLogin={handleLogin} />
  }

  return (
    <div className="flex min-h-screen md:h-screen bg-surface flex-col md:flex-row">
      <SessionManager
        user={authUser}
        communityCount={communityCount}
        activeId={activeId}
        sessions={sessions}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        onLogout={handleLogout}
      />
      <main className="flex-1 flex flex-col min-w-0 min-h-0">
        <StatusBar user={authUser} communityCount={communityCount} />
        <ChatWindow
          key={activeId}
          sessionId={activeId}
          initialMessages={activeSession?.messages || []}
          onMessagesChange={(msgs) => handleMessagesChange(activeId, msgs)}
        />
        <CommunityPanel role={authUser.role} onCommunityCount={setCommunityCount} />
      </main>
    </div>
  )
}
