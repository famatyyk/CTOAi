import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getDiffLedger } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET(_request: Request, context: { params: Promise<{ surface: string }> }) {
  const access = await requireControlCenterReadAccess("Control Center diff ledger")
  if (!access.ok) return access.response

  const { surface } = await context.params
  return NextResponse.json(await getDiffLedger(surface))
}
