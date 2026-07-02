"use client"

import { useCallback, useEffect, useState } from "react"
import ChatWindow from "@/components/ChatWindow"
import type { StoredMessage } from "@/lib/sessionStorage"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"
import {
  buildControlCenterChatLog,
  buildControlCenterChatMarkdown,
  buildControlCenterChatMarkdownFileName,
  buildControlCenterChatTranscript,
  buildControlCenterChatTranscriptFileName,
} from "@/lib/chatTranscript"

const STORAGE_KEY = "ctoa_control_center_chat"
const SESSION_ID = "control-center-primary"

type ControlCenterViewer = {
  username: string
  displayName: string
  role: string
}

type SeedAccount = {
  label: string
  username: string
  role: string
}

const SEED_ACCOUNTS: SeedAccount[] = [
  { label: "Community", username: "recruit", role: "member" },
  { label: "Ops", username: "strategos", role: "member" },
  { label: "Owner", username: "famatyyk", role: "owner" },
]

const AUTO_LOGIN_KEY = "ctoa_control_center_seed_autologin_attempted"
const CHAT_LOG_KEY = "ctoa_control_center_chat_log"

const WELCOME_MESSAGE: StoredMessage = {
  role: "assistant",
  content:
    "Jestem podpięty do Control Center. Możemy rozmawiać o lokalnym statusie, evidence packu, audycie i porządkowaniu projektu w jednym miejscu.",
}

function loadMessages(): StoredMessage[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return [WELCOME_MESSAGE]
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return [WELCOME_MESSAGE]
    const messages = parsed.filter((message): message is StoredMessage => {
      return (
        message &&
        typeof message === "object" &&
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string"
      )
    })
    return messages.length ? messages.slice(-80) : [WELCOME_MESSAGE]
  } catch {
    return [WELCOME_MESSAGE]
  }
}

function saveMessages(messages: StoredMessage[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-80)))
  } catch {
    // Chat persistence is helpful, not critical.
  }
}

export default function ControlCenterChatPanel() {
  const [messages, setMessages] = useState<StoredMessage[]>([WELCOME_MESSAGE])
  const [ready, setReady] = useState(false)
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "unauthenticated" | "error">("loading")
  const [viewer, setViewer] = useState<ControlCenterViewer | null>(null)
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [authError, setAuthError] = useState("")
  const [authLoading, setAuthLoading] = useState(false)
  const [autoLoginAttempted, setAutoLoginAttempted] = useState(false)
  const [codeReviewMode, setCodeReviewMode] = useState(true)
  const [showAdvancedSeeds, setShowAdvancedSeeds] = useState(false)
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle")
  const [downloadState, setDownloadState] = useState<"idle" | "ready" | "error">("idle")
  const [markdownState, setMarkdownState] = useState<"idle" | "ready" | "error">("idle")

  const refreshAuth = useCallback(async () => {
    try {
      const response = await fetchWithTimeout("/api/auth?path=me", { cache: "no-store" }, 5000)
      if (!response.ok) {
        setAuthState("unauthenticated")
        setViewer(null)
        return
      }
      const data = (await response.json()) as { user?: { username?: string; display_name?: string; role?: string } }
      if (data.user?.username && data.user.role) {
        setViewer({
          username: data.user.username,
          displayName: data.user.display_name || data.user.username,
          role: data.user.role,
        })
        setAuthState("authenticated")
      } else {
        setViewer(null)
        setAuthState("unauthenticated")
      }
    } catch {
      setViewer(null)
      setAuthState("error")
    }
  }, [])

  const persistChatLog = useCallback(
    (nextMessages: StoredMessage[]) => {
      try {
        window.localStorage.setItem(
          CHAT_LOG_KEY,
          JSON.stringify(
            buildControlCenterChatLog(nextMessages, {
              sessionId: SESSION_ID,
              viewerName: viewer?.displayName || viewer?.username || null,
              viewerRole: viewer?.role || null,
              strictReviewMode: codeReviewMode,
            }),
          ),
        )
      } catch {
        // Auto-log is helpful, not critical.
      }
    },
    [viewer, codeReviewMode],
  )

  const submitSeedLogin = useCallback(
    async (seedUsername: string) => {
      setAuthLoading(true)
      setAuthError("")

      try {
        const response = await fetch("/api/auth/seed-login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ username: seedUsername }),
        })
        const data = (await response.json()) as { user?: { username?: string }; detail?: string; error?: string }
        if (!response.ok) {
          throw new Error(data.detail || data.error || "Seed login failed.")
        }
        if (data.user?.username) {
          await refreshAuth()
        } else {
          throw new Error("Seed login succeeded but no user was returned.")
        }
      } catch (error) {
        setAuthState("unauthenticated")
        setAuthError(error instanceof Error ? error.message : "Seed login failed.")
      } finally {
        setAuthLoading(false)
      }
    },
    [refreshAuth],
  )

  const submitAuth = useCallback(
    async (nextUsername?: string, nextPassword?: string, nextMode?: "login" | "register") => {
      const login = (nextUsername ?? username).trim().toLowerCase()
      const pass = (nextPassword ?? password).trim()
      const action = nextMode ?? mode
      if (!login || !pass) {
        setAuthError("Username and password are required.")
        return
      }

      setAuthLoading(true)
      setAuthError("")

      try {
        const response = await fetch("/api/auth", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            action,
            payload:
              action === "register"
                ? { username: login, password: pass, role: "member" }
                : { username: login, password: pass },
          }),
        })
        const data = (await response.json()) as { user?: { username?: string; display_name?: string; role?: string }; detail?: string; error?: string }
        if (!response.ok) {
          throw new Error(data.detail || data.error || "Authentication failed.")
        }
        if (data.user?.username) {
          await refreshAuth()
        } else {
          throw new Error("Authentication succeeded but no user was returned.")
        }
      } catch (error) {
        setAuthState("unauthenticated")
        setAuthError(error instanceof Error ? error.message : "Authentication failed.")
      } finally {
        setAuthLoading(false)
      }
    },
    [mode, password, refreshAuth, username],
  )

  const handleSeedAccount = useCallback(
    (seed: SeedAccount) => {
      setMode("login")
      setUsername(seed.username)
      setAuthError("")
      void submitSeedLogin(seed.username)
    },
    [submitSeedLogin],
  )

  useEffect(() => {
    setMessages(loadMessages())
    setReady(true)
    refreshAuth()
  }, [refreshAuth])

  useEffect(() => {
    if (typeof window === "undefined") return
    if (autoLoginAttempted || authState !== "unauthenticated") return
    const isLocalHost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    if (!isLocalHost) return
    if (window.localStorage.getItem(AUTO_LOGIN_KEY) === "done") return

    const seed = SEED_ACCOUNTS[0]
    window.localStorage.setItem(AUTO_LOGIN_KEY, "done")
    setAutoLoginAttempted(true)
    setMode("login")
    setUsername(seed.username)
    void submitSeedLogin(seed.username)
  }, [autoLoginAttempted, authState, submitSeedLogin])

  useEffect(() => {
    if (typeof window === "undefined") return
    persistChatLog(messages)
  }, [messages, persistChatLog])

  function handleMessagesChange(nextMessages: StoredMessage[]) {
    setMessages(nextMessages)
    saveMessages(nextMessages)
    persistChatLog(nextMessages)
  }

  function resetChat() {
    handleMessagesChange([WELCOME_MESSAGE])
  }

  async function copyTranscript() {
    try {
      const transcript = buildControlCenterChatTranscript(messages, {
        sessionId: SESSION_ID,
        viewerName: viewer?.displayName || viewer?.username || null,
        viewerRole: viewer?.role || null,
        strictReviewMode: codeReviewMode,
      })
      await navigator.clipboard.writeText(transcript)
      setCopyState("copied")
      window.setTimeout(() => setCopyState("idle"), 1800)
    } catch {
      setCopyState("error")
      window.setTimeout(() => setCopyState("idle"), 2200)
    }
  }

  function downloadTranscript() {
    exportTranscript("txt")
  }

  function exportMarkdown() {
    exportTranscript("md")
  }

  function exportTranscript(format: "txt" | "md") {
    try {
      const generatedAt = new Date().toISOString()
      const metadata = {
        sessionId: SESSION_ID,
        viewerName: viewer?.displayName || viewer?.username || null,
        viewerRole: viewer?.role || null,
        strictReviewMode: codeReviewMode,
        generatedAt,
      }
      const transcript =
        format === "md" ? buildControlCenterChatMarkdown(messages, metadata) : buildControlCenterChatTranscript(messages, metadata)
      const fileName =
        format === "md"
          ? buildControlCenterChatMarkdownFileName(SESSION_ID, generatedAt)
          : buildControlCenterChatTranscriptFileName(SESSION_ID, generatedAt)
      const blob = new Blob([transcript], { type: format === "md" ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = fileName
      link.click()
      URL.revokeObjectURL(url)
      if (format === "md") {
        setMarkdownState("ready")
        window.setTimeout(() => setMarkdownState("idle"), 1800)
      } else {
        setDownloadState("ready")
        window.setTimeout(() => setDownloadState("idle"), 1800)
      }
    } catch {
      if (format === "md") {
        setMarkdownState("error")
        window.setTimeout(() => setMarkdownState("idle"), 2200)
      } else {
        setDownloadState("error")
        window.setTimeout(() => setDownloadState("idle"), 2200)
      }
    }
  }


  return (
    <article className="flex h-[78vh] min-h-[36rem] flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#151b33]">
      <div className="flex flex-col gap-3 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Control Center Chat</p>
          <p className="mt-1 text-sm text-slate-400">One embedded chat surface using the existing CTOAi chat engine.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setCodeReviewMode((value) => !value)}
            className={`rounded-2xl border px-4 py-2 text-sm font-bold transition ${
              codeReviewMode ? "border-amber-300/40 bg-amber-300/10 text-amber-100" : "border-white/10 bg-white/[0.04] text-slate-300"
            }`}
          >
            {codeReviewMode ? "Code review mode" : "Standard mode"}
          </button>
          <button
            type="button"
            onClick={copyTranscript}
            className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-bold text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            {copyState === "copied" ? "Copied" : copyState === "error" ? "Copy failed" : "Copy chat"}
          </button>
          <button
            type="button"
            onClick={downloadTranscript}
            className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-bold text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            {downloadState === "ready" ? "Saved" : downloadState === "error" ? "Save failed" : "Save .txt"}
          </button>
          <button
            type="button"
            onClick={exportMarkdown}
            className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-bold text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            {markdownState === "ready" ? "Exported" : markdownState === "error" ? "Export failed" : "Export .md"}
          </button>
          {viewer ? <span className="rounded-full bg-cyan-300/10 px-3 py-2 text-xs text-cyan-100">{viewer.displayName} · {viewer.role}</span> : null}
          <button
            onClick={resetChat}
            className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden bg-[#0e1327]">
        {ready && authState === "authenticated" ? (
          <ChatWindow
            sessionId={SESSION_ID}
            initialMessages={messages}
            onMessagesChange={handleMessagesChange}
            strictReviewMode={codeReviewMode}
          />
        ) : (
          <div className="flex h-full items-center justify-center overflow-y-auto p-6">
            {authState === "loading" ? (
              <div className="text-sm text-slate-500">Checking login...</div>
            ) : (
              <div className="w-full max-w-2xl rounded-3xl border border-white/10 bg-[#151b33] p-6 shadow-2xl shadow-cyan-950/20">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-black text-white">Zaloguj się do czatu</p>
                    <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
                      Czat Control Center potrzebuje aktywnej sesji, żeby wysyłać wiadomości bez błędu 401.
                      Na localhost możesz wejść jednym kliknięciem przez lokalny seed account bez trzymania hasła w kliencie.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={refreshAuth}
                    className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-bold text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
                  >
                    Re-check session
                  </button>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  {SEED_ACCOUNTS.slice(0, 1).map((seed) => (
                    <button
                      key={seed.username}
                      type="button"
                      onClick={() => handleSeedAccount(seed)}
                      disabled={authLoading}
                      className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-left text-xs text-slate-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/10 hover:text-cyan-100 disabled:opacity-50"
                    >
                      <span className="block text-[10px] uppercase tracking-[0.3em] text-slate-500">{seed.label}</span>
                      <span className="mt-1 block font-semibold">{seed.username}</span>
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => setShowAdvancedSeeds((value) => !value)}
                    className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-left text-xs text-slate-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/10 hover:text-cyan-100"
                  >
                    <span className="block text-[10px] uppercase tracking-[0.3em] text-slate-500">
                      {showAdvancedSeeds ? "Hide" : "Show"} roles
                    </span>
                    <span className="mt-1 block font-semibold">Operator / Owner</span>
                  </button>
                  {showAdvancedSeeds
                    ? SEED_ACCOUNTS.slice(1).map((seed) => (
                        <button
                          key={seed.username}
                          type="button"
                          onClick={() => handleSeedAccount(seed)}
                          disabled={authLoading}
                          className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-left text-xs text-slate-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/10 hover:text-cyan-100 disabled:opacity-50"
                        >
                          <span className="block text-[10px] uppercase tracking-[0.3em] text-slate-500">{seed.label}</span>
                          <span className="mt-1 block font-semibold">{seed.username}</span>
                        </button>
                      ))
                    : null}
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className={`rounded-2xl border px-4 py-3 text-sm font-bold ${mode === "login" ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100" : "border-white/10 bg-white/[0.04] text-slate-300"}`}
                  >
                    Login
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("register")}
                    className={`rounded-2xl border px-4 py-3 text-sm font-bold ${mode === "register" ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100" : "border-white/10 bg-white/[0.04] text-slate-300"}`}
                  >
                    Register
                  </button>
                  <button
                    type="button"
                    onClick={() => void submitAuth()}
                    disabled={authLoading}
                    className="rounded-2xl bg-cyan-300 px-4 py-3 text-sm font-black text-[#111629] transition hover:bg-cyan-200 disabled:opacity-50"
                  >
                    {authLoading ? "Signing in..." : mode === "login" ? "Sign in" : "Create account"}
                  </button>
                </div>

                <div className="mt-3 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => handleSeedAccount(SEED_ACCOUNTS[0])}
                    disabled={authLoading}
                    className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-xs font-bold text-cyan-100 transition hover:bg-cyan-300/20 disabled:opacity-50"
                  >
                    Auto-login local seed
                  </button>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <input
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    placeholder="Username"
                    className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-200/60"
                  />
                  <input
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Password"
                    type="password"
                    className="rounded-2xl border border-white/10 bg-[#0e1327] px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-200/60"
                  />
                </div>
                {authError ? <p className="mt-3 text-sm text-pink-200">{authError}</p> : null}
                <p className="mt-4 text-xs leading-5 text-slate-500">
                  Default seed is member. Extra operator/owner seeds are hidden unless you expand them.{" "}
                  {codeReviewMode
                    ? "Draft answers without tests or edge-case handling are blocked."
                    : "Draft answers are shown with a review badge."}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Session log is saved locally and can be copied or downloaded as a text transcript.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
