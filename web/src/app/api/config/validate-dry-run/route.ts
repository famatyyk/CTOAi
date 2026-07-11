import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { validateConfigDryRun } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function POST(request: Request) {
  const access = await requireControlCenterReadAccess("Control Center configuration dry run")
  if (!access.ok) return access.response

  let payload: unknown

  try {
    payload = await request.json()
  } catch {
    payload = null
  }

  const result = validateConfigDryRun(payload)
  return NextResponse.json(result, { status: result.ok ? 200 : 400 })
}
