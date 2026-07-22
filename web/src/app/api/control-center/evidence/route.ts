import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import {
  CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS,
  withControlCenterPrivateNoStore,
} from "@/app/api/control-center/privateNoStore"
import { collectControlCenterEvidence } from "@/lib/controlCenterEvidence"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center evidence")
  if (!access.ok) return withControlCenterPrivateNoStore(access.response)

  const evidence = await collectControlCenterEvidence()
  return NextResponse.json(evidence, { headers: CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS })
}
