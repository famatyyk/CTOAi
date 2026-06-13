"use client"

import { useEffect, useState } from "react"
import { Activity, Database, Cpu, Users } from "lucide-react"
import { AuthUser } from "@/components/LoginPanel"

interface Status {
  runner: string
  model: string
}

interface StatusBarProps {
  user: AuthUser
  communityCount: number
}

export default function StatusBar({ user, communityCount }: StatusBarProps) {
  const [status, setStatus] = useState<Status | null>(null)

  useEffect(() => {
    const check = () =>
      fetch("/api/status")
        .then((r) => r.json())
        .then(setStatus)
        .catch(() => setStatus(null))
    check()
    const t = setInterval(check, 30000)
    return () => clearInterval(t)
  }, [])

  const dot = status ? "bg-emerald-500" : "bg-red-500"

  return (
    <div className="flex items-center gap-4 px-4 py-2 border-b border-border text-xs text-zinc-400">
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${dot} animate-pulse`} />
        <span>VPS 116.202.96.250</span>
      </div>

      <div className="flex items-center gap-1 text-emerald-300">
        <Users className="w-3 h-3" />
        {communityCount} community
      </div>

      <div className="px-2 py-0.5 rounded-full border border-zinc-700 text-zinc-300">
        @{user.username}
      </div>

      {status && (
        <>
          <div className="flex items-center gap-1">
            <Cpu className="w-3 h-3" />
            {status.model}
          </div>
          <div className="flex items-center gap-1">
            <Activity className="w-3 h-3" />
            runner: {status.runner}
          </div>
        </>
      )}
      <div className="flex items-center gap-1 ml-auto">
        <Database className="w-3 h-3" />
        PostgreSQL - backup 06:00
      </div>
    </div>
  )
}
