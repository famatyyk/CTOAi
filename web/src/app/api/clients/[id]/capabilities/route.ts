import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getClientCapabilities } from "@/lib/tibiaOperationalState"

export const runtime = "nodejs"

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const access = await requireControlCenterReadAccess("Control Center client capabilities")
  if (!access.ok) return access.response

  const { id } = await context.params
  const capabilities = await getClientCapabilities(id)

  if (!capabilities) {
    return NextResponse.json(
      {
        error: "client_not_found",
        client_id: id,
      },
      { status: 404 },
    )
  }

  return NextResponse.json(capabilities)
}
