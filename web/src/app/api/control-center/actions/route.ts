import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { getServerApiUrl } from "@/lib/config"
import { resolveControlCenterViewer } from "@/lib/controlCenterAuth"
import {
  listControlCenterActions,
  runControlCenterAction,
  ControlCenterAuthorizationError,
  sanitizeControlCenterActionOutput,
} from "@/lib/controlCenterActions"
import { canRunControlCenterAction } from "@/lib/controlCenterPolicy"
import { validateSameOriginRequest } from "@/lib/requestOriginGuard"
import { CTOA_TOKEN_COOKIE_NAME } from "@/lib/authCookies"

export const runtime = "nodejs"

export function validateControlCenterActionRequestOrigin(request: Request): { ok: boolean; error?: string } {
  return validateSameOriginRequest(request, { requestLabel: "Control Center action" })
}

async function loadViewer() {
  const token = (await cookies()).get(CTOA_TOKEN_COOKIE_NAME)?.value
  return resolveControlCenterViewer(token, getServerApiUrl())
}

function sanitizeControlCenterActionError(value: string): string {
  return sanitizeControlCenterActionOutput(value, 1200) || "Control Center action failed."
}

export async function GET() {
  const viewer = await loadViewer()
  const actions = viewer.viewer
    ? listControlCenterActions().filter((action) => canRunControlCenterAction(action, viewer.viewer?.role).allowed)
    : []

  return NextResponse.json({
    generatedAt: new Date().toISOString(),
    actions,
    authStatus: viewer.authStatus,
    viewer: viewer.viewer,
  })
}

export async function POST(request: Request) {
  try {
    const originGate = validateControlCenterActionRequestOrigin(request)
    if (!originGate.ok) {
      return NextResponse.json({ ok: false, error: originGate.error }, { status: 403 })
    }

    const viewer = await loadViewer()
    const body = (await request.json()) as {
      actionId?: string
      confirmation?: string
      reason?: string
      dryRun?: boolean
    }

    if (!body.actionId) {
      return NextResponse.json({ ok: false, error: "Missing actionId." }, { status: 400 })
    }

    const result = await runControlCenterAction({
      actionId: body.actionId,
      confirmation: body.confirmation,
      reason: body.reason,
      dryRun: body.dryRun,
      actor: viewer.viewer,
    })

    return NextResponse.json({ ok: result.ok, result }, { status: result.ok ? 200 : 500 })
  } catch (error) {
    if (error instanceof ControlCenterAuthorizationError) {
      return NextResponse.json({ ok: false, error: sanitizeControlCenterActionError(error.message) }, { status: error.statusCode })
    }
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? sanitizeControlCenterActionError(error.message) : "Control Center action failed.",
      },
      { status: 400 },
    )
  }
}
