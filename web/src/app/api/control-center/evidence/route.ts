import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { collectControlCenterEvidence } from "@/lib/controlCenterEvidence"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center evidence")
  if (!access.ok) return access.response

  const evidence = await collectControlCenterEvidence()
  return NextResponse.json(evidence)
}
