import { NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"

const API_URL = getServerApiUrl()

export async function GET() {
  try {
    const r = await fetch(API_URL + "/api/status", { cache: "no-store" })
    const data = await r.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ runner: "offline", model: "unknown" }, { status: 503 })
  }
}
