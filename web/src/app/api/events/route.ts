import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getTelemetryEvents } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center telemetry events")
  if (!access.ok) return access.response

  return NextResponse.json(await getTelemetryEvents())
}
