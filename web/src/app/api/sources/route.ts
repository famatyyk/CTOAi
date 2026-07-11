import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getTibiaSources } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center source inventory")
  if (!access.ok) return access.response

  return NextResponse.json(await getTibiaSources())
}
