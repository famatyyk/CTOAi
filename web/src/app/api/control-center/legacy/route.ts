import { cookies } from "next/headers"
import { NextResponse } from "next/server"
import { getServerApiUrl } from "@/lib/config"

export const runtime = "nodejs"

type LegacyFetchResult = {
  ok: boolean
  status: number
  body: unknown
}

const API_URL = getServerApiUrl()

async function backendGet(path: string): Promise<LegacyFetchResult> {
  const token = (await cookies()).get("ctoa_token")?.value
  try {
    const response = await fetch(`${API_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    })
    const body = await response.json().catch(() => ({}))
    return { ok: response.ok, status: response.status, body }
  } catch (error) {
    return {
      ok: false,
      status: 503,
      body: { detail: error instanceof Error ? error.message : "Backend unavailable" },
    }
  }
}

export async function GET() {
  const [dashboard, agentsStatus, releaseEvidence, commandDictionary, runnerLog] = await Promise.all([
    backendGet("/api/dashboard"),
    backendGet("/api/agents/status"),
    backendGet("/api/dashboard/release-evidence"),
    backendGet("/api/commands/dictionary"),
    backendGet("/api/logs?target=runner&lines=80"),
  ])

  return NextResponse.json({
    generatedAt: new Date().toISOString(),
    source: API_URL,
    capabilities: {
      dashboard,
      agentsStatus,
      releaseEvidence,
      commandDictionary,
      runnerLog,
    },
  })
}
