"use client"
import { useState, useRef, useEffect } from "react"
import { Send, Bot, User } from "lucide-react"
import ReactMarkdown from "react-markdown"

interface Message { role: "user" | "assistant"; content: string }

interface Props {
  sessionId: string
  initialMessages: Message[]
  onMessagesChange: (msgs: Message[]) => void
}

export default function ChatWindow({ initialMessages, onMessagesChange }: Props) {
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
        body: JSON.stringify({ messages: next }),
      })
      if (!res.ok) throw new Error("HTTP " + res.status)
      const data = await res.json()
      const reply: Message = { role: "assistant", content: data.content ?? data.message ?? JSON.stringify(data) }
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
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 opacity-40">
            <div className="w-16 h-16 rounded-2xl bg-accent/20 border border-accent/30 flex items-center justify-center">
              <Bot className="w-8 h-8 text-accent" />
            </div>
            <p className="text-lg font-medium">CTOAi - STRATEGOS</p>
            <p className="text-sm">Stworzony przez Famatyyka aka Jakuba P.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={"flex gap-3 " + (m.role === "user" ? "justify-end" : "justify-start")}>
            {m.role === "assistant" && (
              <div className="w-8 h-8 rounded-xl bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-accent" />
              </div>
            )}
            <div className={"max-w-[92%] sm:max-w-[85%] lg:max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words " + (m.role === "user" ? "bg-accent text-white rounded-br-sm" : "bg-panel border border-border rounded-bl-sm")}>
              {m.role === "assistant"
                ? <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{m.content}</ReactMarkdown>
                : <p className="whitespace-pre-wrap break-words">{m.content}</p>}
            </div>
            {m.role === "user" && (
              <div className="w-8 h-8 rounded-xl bg-zinc-700/70 border border-zinc-600/40 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-zinc-300" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3 items-end">
            <div className="w-8 h-8 rounded-xl bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-accent" />
            </div>
            <div className="bg-panel border border-border rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-300 animate-bounce" style={{ animationDelay: "-0.3s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-300 animate-bounce" style={{ animationDelay: "-0.15s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-300 animate-bounce" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-border px-4 py-4">
        <div className="flex gap-3 items-end bg-panel border border-border rounded-2xl px-4 py-3 focus-within:border-accent transition-colors">
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
            className="flex-1 bg-transparent resize-none outline-none text-sm text-white placeholder-zinc-500 max-h-40"
          />
          <button onClick={send} disabled={!input.trim() || loading} className="p-1.5 rounded-xl bg-accent text-white disabled:opacity-30 hover:bg-violet-600 transition-colors shrink-0">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-2">Enter wyslij - Shift+Enter nowa linia</p>
      </div>
    </div>
  )
}
