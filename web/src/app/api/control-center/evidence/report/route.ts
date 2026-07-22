import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import {
  CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS,
  withControlCenterPrivateNoStore,
} from "@/app/api/control-center/privateNoStore"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { readBoundedControlCenterMarkdownReport, ControlCenterMarkdownReportTooLargeError } from "@/lib/controlCenterMarkdownReportFile"
import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center release evidence report")
  if (!access.ok) return withControlCenterPrivateNoStore(access.response)

  const filePath = getControlCenterEvidenceConfig().evidenceMarkdownPath

  try {
    const body = await readBoundedControlCenterMarkdownReport(filePath)
    return new NextResponse(sanitizeControlCenterMarkdownReport(body), {
      status: 200,
      headers: {
        ...CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS,
        "Content-Type": "text/markdown; charset=utf-8",
      },
    })
  } catch (error) {
    if (error instanceof ControlCenterMarkdownReportTooLargeError) {
      return NextResponse.json(
        { error: "Evidence markdown is too large to display safely." },
        { status: 413, headers: CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS },
      )
    }
    return NextResponse.json(
      { error: "Evidence markdown not available yet." },
      { status: 404, headers: CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS },
    )
  }
}
