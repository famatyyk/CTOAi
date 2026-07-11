import { cookies } from "next/headers"
import { NextResponse } from "next/server"
import { CTOA_TOKEN_COOKIE_NAME } from "@/lib/authCookies"
import { getServerApiUrl } from "@/lib/config"
import { resolveControlCenterViewer } from "@/lib/controlCenterAuth"
import { authorizeControlCenterEvidenceAccess } from "@/lib/controlCenterEvidenceAccess"

export async function requireControlCenterReadAccess(surfaceLabel: string) {
  const token = (await cookies()).get(CTOA_TOKEN_COOKIE_NAME)?.value
  const access = authorizeControlCenterEvidenceAccess(await resolveControlCenterViewer(token, getServerApiUrl()), surfaceLabel)

  if (!access.ok) {
    return {
      ok: false as const,
      response: NextResponse.json(access.body, { status: access.status }),
    }
  }

  return {
    ok: true as const,
    viewer: access.viewer,
  }
}
