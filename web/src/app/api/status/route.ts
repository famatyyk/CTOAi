import { NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"

const API_URL = process.env.VPS_API_URL ?? "http://127.0.0.1:8011";

export async function GET() {
  try {
    const r = await fetch(API_URL + "/api/status", { cache: "no-store" })
    const data = await r.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ runner: "offline", model: "unknown" }, { status: 503 })
  }
}
