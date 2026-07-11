import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getLatestUpdates } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center latest updates")
  if (!access.ok) return access.response

  return NextResponse.json(await getLatestUpdates())
}
