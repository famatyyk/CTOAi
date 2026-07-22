import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import {
  CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS,
  withControlCenterPrivateNoStore,
} from "@/app/api/control-center/privateNoStore"
import { collectControlCenterOps } from "@/lib/controlCenterOps"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center ops evidence")
  if (!access.ok) return withControlCenterPrivateNoStore(access.response)

  const ops = await collectControlCenterOps()
  return NextResponse.json(ops, { headers: CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS })
}
