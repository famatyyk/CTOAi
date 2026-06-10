"use client"
import { useState, useRef, useEffect } from "react"
import { Send, Loader2 } from "lucide-react"
import ReactMarkdown from "react-markdown"

interface Message { role: "user" | "assistant"; content: string }

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://116.202.96.250:8000"

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    const next: Message[] = [...messages, { role: "user", content: text }]
    setMessages(next)
    setInput("")
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMessages([...next, { role: "assistant", content: data.content ?? data.message ?? JSON.stringify(data) }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error"
      setMessages([...next, { role: "assistant", content: `⚠️ Error: ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 opacity-40">
            <div className="text-5xl">🤖</div>
            <p className="text-lg font-medium">CTOAi</p>
            <p className="text-sm">Qwen2.5-Coder · VPS 116.202.96.250</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {m.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-xs shrink-0">AI</div>
            )}
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              m.role === "user"
                ? "bg-accent text-white rounded-br-sm"
                : "bg-panel border border-border rounded-bl-sm"
            }`}>
              {m.role === "assistant"
                ? <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{m.content}</ReactMarkdown>
                : <p>{m.content}</p>}
            </div>
            {m.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs shrink-0">U</div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-xs shrink-0">AI</div>
            <div className="bg-panel border border-border rounded-2xl rounded-bl-sm px-4 py-3">
              <Loader2 className="w-4 h-4 animate-spin opacity-60" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-4">
        <div className="flex gap-3 items-end bg-panel border border-border rounded-2xl px-4 py-3 focus-within:border-accent transition-colors">
          <textarea
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Napisz wiadomość…"
            className="flex-1 bg-transparent resize-none outline-none text-sm text-white placeholder-zinc-500 max-h-40"
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="p-1.5 rounded-xl bg-accent text-white disabled:opacity-30 hover:bg-violet-600 transition-colors shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-2">Enter wyślij · Shift+Enter nowa linia</p>
      </div>
    </div>
  )
}
