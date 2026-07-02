import { NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

const API_URL = getServerApiUrl()

export async function GET() {
  try {
    const r = await fetchWithTimeout(API_URL + "/api/status", { cache: "no-store" }, 4000)
    const data = await r.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ runner: "offline", model: "unknown" }, { status: 503 })
  }
}
