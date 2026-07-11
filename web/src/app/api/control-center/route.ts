import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { controlCenterSnapshot } from "@/lib/controlCenterSnapshot"
import { getServerApiUrl } from "@/lib/config"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"
import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"
import { getClients, getLatestUpdates, getTibiaSources } from "@/lib/tibiaOperationalState"

function sanitizeControlCenterProbeError(value: string): string {
  return sanitizeControlCenterMarkdownReport(value).trim() || "Backend API probe failed."
}

async function localOperationalState() {
  const [sources, clients, updates] = await Promise.all([getTibiaSources(), getClients(), getLatestUpdates()])

  return {
    generatedAt: sources.generated_at,
    sourceStates: sources.sources.map((source) => ({
      sourceKind: source.source_kind,
      status: source.status,
      freshness: source.freshness,
      parserStatus: source.parser.status,
      nextAction: source.next_action,
    })),
    clientStates: clients.clients.map((client) => ({
      clientId: client.client_id,
      status: client.status,
      protocolStatus: client.protocol_status,
      heartbeatStatus: client.heartbeat.status,
      evidenceStatus: client.evidence_status,
      safeFallback: client.safe_fallback,
      nextAction: client.next_action,
    })),
    latestEventCount: updates.events.length,
  }
}

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center snapshot")
  if (!access.ok) return access.response

  const apiUrl = getServerApiUrl()
  const operational = await localOperationalState()

  try {
    const response = await fetchWithTimeout(`${apiUrl}/api/status`, { cache: "no-store" }, 4000)
    const status = await response.json()

    return NextResponse.json({
      ...controlCenterSnapshot,
      operational,
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
      operational,
      backend: {
        apiUrl,
        reachable: false,
        summary: error instanceof Error ? sanitizeControlCenterProbeError(error.message) : "Backend API probe failed.",
      },
    })
  }
}
