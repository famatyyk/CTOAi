"use client"

import { useEffect, useState } from "react"
import ChatWindow from "@/components/ChatWindow"
import type { StoredMessage } from "@/lib/sessionStorage"

const STORAGE_KEY = "ctoa_control_center_chat"
const SESSION_ID = "control-center-primary"

const WELCOME_MESSAGE: StoredMessage = {
  role: "assistant",
  content:
    "Jestem podpięty do Control Center. Możemy rozmawiać o VPS, Dockerze, GitHubie, bot runtime i porządkowaniu projektu w jednym miejscu.",
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

  useEffect(() => {
    setMessages(loadMessages())
    setReady(true)
  }, [])

  function handleMessagesChange(nextMessages: StoredMessage[]) {
    setMessages(nextMessages)
    saveMessages(nextMessages)
  }

  function resetChat() {
    handleMessagesChange([WELCOME_MESSAGE])
  }

  return (
    <article className="overflow-hidden rounded-3xl border border-white/10 bg-[#151b33]">
      <div className="flex flex-col gap-3 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black">Control Center Chat</p>
          <p className="mt-1 text-sm text-slate-400">One embedded chat surface using the existing CTOAi chat engine.</p>
        </div>
        <button
          onClick={resetChat}
          className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-300/40 hover:text-white"
        >
          Reset
        </button>
      </div>

      <div className="h-[620px] bg-[#0e1327]">
        {ready ? (
          <ChatWindow sessionId={SESSION_ID} initialMessages={messages} onMessagesChange={handleMessagesChange} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading chat...</div>
        )}
      </div>
    </article>
  )
}
