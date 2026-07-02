"use client"
import { useState, useRef, useEffect } from "react"
import { Send, Bot, User } from "lucide-react"
import ReactMarkdown from "react-markdown"
import {
  decideControlCenterChatPublication,
  evaluateControlCenterChatTemplate,
  type ChatQualityAssessment,
} from "@/lib/chatQuality"
import type { StoredMessage } from "@/lib/sessionStorage"

interface Message extends StoredMessage {
  quality?: ChatQualityAssessment
}

interface Props {
  sessionId: string
  initialMessages: Message[]
  onMessagesChange: (msgs: Message[]) => void
  strictReviewMode?: boolean
}

export default function ChatWindow({ initialMessages, onMessagesChange, strictReviewMode = false }: Props) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    const next: Message[] = [...messages, { role: "user", content: text }]
    setMessages(next)
    onMessagesChange(next)
    setInput("")
    setLoading(true)
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ messages: next }),
      })
      if (!res.ok) throw new Error("HTTP " + res.status)
      const data = await res.json()
      const quality = data.quality as ChatQualityAssessment | undefined
      const template = typeof data.content === "string" ? evaluateControlCenterChatTemplate(data.content) : undefined
      const publication = quality
        ? decideControlCenterChatPublication(quality, strictReviewMode, template)
        : { blocked: false, label: "published", detail: "" }
      const content =
        publication.blocked && quality
          ? [
              publication.label === "blocked" ? "Hard review blocked publication." : "Code review mode blocked publication.",
              "",
              "Reason: the answer still looks like a draft.",
              "",
              ...(quality.issues.length ? ["Open issues:", ...quality.issues.map((issue) => `- ${issue}`)] : ["Open issues: none recorded."]),
              ...(publication.missingTemplateSections?.length
                ? ["", "Missing template sections:", ...publication.missingTemplateSections.map((section) => `- ${section}`)]
                : []),
            ].join("\n")
          : data.content ?? data.message ?? JSON.stringify(data)
      const reply: Message = {
        role: "assistant",
        content,
        quality,
        publicationState: publication.blocked ? "blocked" : "published",
        publicationNote:
          publication.detail || (publication.missingTemplateSections?.length ? `Missing: ${publication.missingTemplateSections.join(", ")}` : undefined),
      }
      const final = [...next, reply]
      setMessages(final)
      onMessagesChange(final)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error"
      const err: Message[] = [...next, { role: "assistant", content: "Error: " + msg }]
      setMessages(err)
      onMessagesChange(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 [scrollbar-gutter:stable]">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center opacity-40">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-accent/30 bg-accent/20">
                <Bot className="h-8 w-8 text-accent" />
              </div>
              <p className="text-lg font-medium">CTOAi - STRATEGOS</p>
              <p className="text-sm">Stworzony przez Famatyyka aka Jakuba P.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={"flex gap-3 " + (m.role === "user" ? "justify-end" : "justify-start")}>
              {m.role === "assistant" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-accent/30 bg-accent/20">
                  <Bot className="h-4 w-4 text-accent" />
                </div>
              )}
              <div className={"max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words sm:max-w-[80%] lg:max-w-[72%] " + (m.role === "user" ? "bg-accent text-white rounded-br-sm" : "bg-panel border border-border rounded-bl-sm")}>
                {m.role === "assistant"
                  ? (
                    <div className="space-y-3">
                      {m.publicationState === "blocked" ? (
                        <div className="rounded-2xl border border-pink-300/20 bg-pink-300/10 p-4">
                          <p className="text-xs font-bold uppercase tracking-[0.2em] text-pink-100">Publication blocked</p>
                          <p className="mt-2 whitespace-pre-wrap text-sm text-pink-100/90">{m.content}</p>
                          {m.publicationNote ? <p className="mt-2 text-xs text-pink-100/70">{m.publicationNote}</p> : null}
                        </div>
                      ) : (
                        <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{m.content}</ReactMarkdown>
                      )}
                      {m.quality ? (
                        <div
                          className={
                            "rounded-xl border px-3 py-2 text-xs " +
                            (m.quality.level === "approved"
                              ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
                              : m.quality.level === "review"
                                ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
                                : "border-pink-300/20 bg-pink-300/10 text-pink-100")
                          }
                        >
                          <div className="font-bold uppercase tracking-[0.2em]">
                            Quality gate: {m.quality.level} · {m.quality.score}/100
                          </div>
                          {m.quality.issues.length > 0 ? <p className="mt-1 leading-5">{m.quality.issues.join(" ")}</p> : null}
                        </div>
                      ) : null}
                    </div>
                  )
                  : <p className="whitespace-pre-wrap break-words">{m.content}</p>}
              </div>
              {m.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-zinc-600/40 bg-zinc-700/70">
                  <User className="h-4 w-4 text-zinc-300" />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex items-end gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-accent/30 bg-accent/20">
                <Bot className="h-4 w-4 text-accent" />
              </div>
              <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border border-border bg-panel px-4 py-3">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-300" style={{ animationDelay: "-0.3s" }} />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-300" style={{ animationDelay: "-0.15s" }} />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-300" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="shrink-0 border-t border-border px-4 py-4">
        <div className="flex items-end gap-3 rounded-2xl border border-border bg-panel px-4 py-3 transition-colors focus-within:border-accent">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = "auto"
              e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px"
            }}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Napisz wiadomosc..."
            className="max-h-40 flex-1 resize-none bg-transparent text-sm text-white outline-none placeholder-zinc-500"
          />
          <button onClick={send} disabled={!input.trim() || loading} className="shrink-0 rounded-xl bg-accent p-1.5 text-white transition-colors hover:bg-violet-600 disabled:opacity-30">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-2">Enter wyslij - Shift+Enter nowa linia</p>
      </div>
    </div>
  )
}
