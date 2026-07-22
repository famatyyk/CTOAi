import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import {
  ControlCenterAuthorizationError,
  ControlCenterPreflightError,
  getControlCenterActionSchemaVersion,
  listControlCenterActionCapabilities,
  projectControlCenterActionResult,
  runControlCenterAction,
  sanitizeControlCenterActionOutput,
} from "@/lib/controlCenterActions"
import { validateSameOriginRequest } from "@/lib/requestOriginGuard"

export const runtime = "nodejs"

const privateNoStore = { "Cache-Control": "private, no-store" }

function withPrivateNoStore(response: Response): Response {
  response.headers.set("Cache-Control", "private, no-store")
  return response
}

type ActionRequestBody = {
  actionId?: unknown
  confirmation?: unknown
  reason?: unknown
  proofId?: unknown
  dryRun?: unknown
}

export function validateControlCenterActionRequestOrigin(request: Request): { ok: boolean; error?: string } {
  return validateSameOriginRequest(request, { requestLabel: "Control Center action" })
}

function sanitizeControlCenterActionError(value: string): string {
  return sanitizeControlCenterActionOutput(value, 1200) || "Control Center action failed."
}

function stringField(value: unknown, maximumLength: number, trim = false): string | undefined {
  if (typeof value !== "string") return undefined
  const normalized = trim ? value.trim() : value
  return normalized.length <= maximumLength ? normalized : undefined
}

function parseActionRequest(body: ActionRequestBody):
  | {
      ok: true
      value: {
        actionId: string
        confirmation?: string
        reason?: string
        proofId?: string
        dryRun: boolean
      }
    }
  | { ok: false; error: string } {
  const actionId = stringField(body.actionId, 120, true)
  if (!actionId) return { ok: false, error: "Missing or invalid actionId." }
  if (body.dryRun !== undefined && typeof body.dryRun !== "boolean") {
    return { ok: false, error: "dryRun must be a boolean." }
  }
  if (body.confirmation !== undefined && typeof body.confirmation !== "string") {
    return { ok: false, error: "confirmation must be a string." }
  }
  if (body.reason !== undefined && typeof body.reason !== "string") {
    return { ok: false, error: "reason must be a string." }
  }
  if (body.proofId !== undefined && typeof body.proofId !== "string") {
    return { ok: false, error: "proofId must be a string." }
  }

  const confirmation = stringField(body.confirmation, 256)
  const reason = stringField(body.reason, 1024)
  const proofId = stringField(body.proofId, 128)
  if ((body.confirmation !== undefined && confirmation === undefined) || (body.reason !== undefined && reason === undefined)) {
    return { ok: false, error: "Action text exceeds the allowed length." }
  }
  if (body.proofId !== undefined && proofId === undefined) return { ok: false, error: "Invalid proofId." }

  return { ok: true, value: { actionId, confirmation, reason, proofId, dryRun: body.dryRun !== false } }
}

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center action capabilities")
  if (!access.ok) return withPrivateNoStore(access.response)

  const payload = await listControlCenterActionCapabilities({ actor: access.viewer })
  return NextResponse.json(payload, { headers: privateNoStore })
}

export async function POST(request: Request) {
  try {
    const originGate = validateControlCenterActionRequestOrigin(request)
    if (!originGate.ok) {
      return NextResponse.json({ ok: false, error: originGate.error }, { status: 403, headers: privateNoStore })
    }

    const access = await requireControlCenterReadAccess("Control Center action execution")
    if (!access.ok) return withPrivateNoStore(access.response)

    const parsed = parseActionRequest((await request.json()) as ActionRequestBody)
    if (!parsed.ok) {
      return NextResponse.json({ ok: false, error: parsed.error }, { status: 400, headers: privateNoStore })
    }

    const result = await runControlCenterAction({ ...parsed.value, actor: access.viewer })
    return NextResponse.json(
      { ok: result.ok, result: projectControlCenterActionResult(result) },
      { status: result.ok ? 200 : 500, headers: privateNoStore },
    )
  } catch (error) {
    if (error instanceof ControlCenterPreflightError) {
      return NextResponse.json(
        { ok: false, error: sanitizeControlCenterActionError(error.message), preflight: error.preflight },
        { status: error.statusCode, headers: privateNoStore },
      )
    }
    if (error instanceof ControlCenterAuthorizationError) {
      return NextResponse.json(
        { ok: false, error: sanitizeControlCenterActionError(error.message) },
        { status: error.statusCode, headers: privateNoStore },
      )
    }
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? sanitizeControlCenterActionError(error.message) : "Control Center action failed.",
      },
      { status: 400, headers: privateNoStore },
    )
  }
}

export { getControlCenterActionSchemaVersion }
