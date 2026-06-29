import { NextResponse } from "next/server"
import { controlCenterSnapshot } from "@/lib/controlCenterSnapshot"
import { getServerApiUrl } from "@/lib/config"

export async function GET() {
  const apiUrl = getServerApiUrl()

  try {
    const response = await fetch(`${apiUrl}/api/status`, { cache: "no-store" })
    const status = await response.json()

    return NextResponse.json({
      ...controlCenterSnapshot,
      backend: {
        apiUrl,
        reachable: response.ok,
        summary: response.ok ? "Backend API reachable." : `Backend API returned HTTP ${response.status}.`,
        status,
      },
    })
  } catch (error) {
    return NextResponse.json({
      ...controlCenterSnapshot,
      backend: {
        apiUrl,
        reachable: false,
        summary: error instanceof Error ? error.message : "Backend API probe failed.",
      },
    })
  }
}
