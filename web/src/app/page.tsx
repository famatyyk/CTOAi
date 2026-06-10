import ChatWindow from "@/components/ChatWindow"
import StatusBar from "@/components/StatusBar"
import { MessageSquare } from "lucide-react"

export default function Home() {
  return (
    <div className="flex h-screen bg-surface">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border flex flex-col bg-panel shrink-0">
        <div className="px-4 py-5 border-b border-border">
          <h1 className="text-white font-semibold tracking-tight">CTOAi</h1>
          <p className="text-xs text-zinc-500 mt-0.5">AI Operations Platform</p>
        </div>
        <nav className="flex-1 px-2 py-3 space-y-1">
          <button className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg bg-accent/20 text-white text-sm">
            <MessageSquare className="w-4 h-4" />
            <span>Chat</span>
          </button>
        </nav>
        <div className="px-4 py-3 border-t border-border">
          <p className="text-xs text-zinc-600">Qwen2.5-Coder 1.5B</p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0">
        <StatusBar />
        <ChatWindow />
      </main>
    </div>
  )
}
