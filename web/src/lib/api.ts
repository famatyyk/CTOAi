import { getPublicApiUrl } from "@/lib/config"

const API_URL = getPublicApiUrl()

export async function streamChat(messages: { role: string; content: string }[]) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res
}

export async function getStatus() {
  const res = await fetch(`${API_URL}/api/status`, { cache: "no-store" })
  if (!res.ok) return null
  return res.json()
}
