import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { collectControlCenterOps } from "@/lib/controlCenterOps"
import { projectControlCenterOpsForPublicApi } from "@/lib/controlCenterPublicOps"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"
export const revalidate = 0

const PRIVATE_NO_STORE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0",
  Pragma: "no-cache",
  Vary: "Cookie",
}

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center public ops")
  if (!access.ok) {
    for (const [name, value] of Object.entries(PRIVATE_NO_STORE_HEADERS)) {
      access.response.headers.set(name, value)
    }
    return access.response
  }

  try {
    const publicOps = projectControlCenterOpsForPublicApi(await collectControlCenterOps())
    if (!publicOps) {
      return unavailableResponse()
    }
    return NextResponse.json(publicOps, { headers: PRIVATE_NO_STORE_HEADERS })
  } catch {
    return unavailableResponse()
  }
}

function unavailableResponse() {
  return NextResponse.json({ ok: false, error: "Control Center public status is unavailable." }, { status: 503, headers: PRIVATE_NO_STORE_HEADERS })
}
