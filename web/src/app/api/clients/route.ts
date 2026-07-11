import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getClients } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center client inventory")
  if (!access.ok) return access.response

  return NextResponse.json(await getClients())
}
