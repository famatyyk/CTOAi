import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { collectControlCenterOps } from "@/lib/controlCenterOps"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center ops evidence")
  if (!access.ok) return access.response

  const ops = await collectControlCenterOps()
  return NextResponse.json(ops)
}
