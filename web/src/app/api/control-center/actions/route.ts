import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { getServerApiUrl } from "@/lib/config"
import { resolveControlCenterViewer } from "@/lib/controlCenterAuth"
import { listControlCenterActions, runControlCenterAction, ControlCenterAuthorizationError } from "@/lib/controlCenterActions"

export const runtime = "nodejs"

async function loadViewer() {
  const token = (await cookies()).get("ctoa_token")?.value
  return resolveControlCenterViewer(token, getServerApiUrl())
}

export async function GET() {
  const viewer = await loadViewer()
  return NextResponse.json({
    generatedAt: new Date().toISOString(),
    actions: listControlCenterActions(),
    authStatus: viewer.authStatus,
    viewer: viewer.viewer,
  })
}

export async function POST(request: Request) {
  try {
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
      return NextResponse.json({ ok: false, error: error.message }, { status: error.statusCode })
    }
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Control Center action failed.",
      },
      { status: 400 },
    )
  }
}
