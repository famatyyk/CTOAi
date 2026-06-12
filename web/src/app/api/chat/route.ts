import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

export const maxDuration = 60
export const dynamic = "force-dynamic"

const API_URL = process.env.VPS_API_URL ?? "http://116.202.96.250:8001"

export async function POST(req: NextRequest) {
  const body = await req.json()
  const token = (await cookies()).get("ctoa_token")?.value
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 55000)
  try {
    const r = await fetch(API_URL + "/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })

    const data = await r.json()
    return NextResponse.json(data, { status: r.status })
  } finally {
    clearTimeout(timer)
  }
}
