import { NextResponse } from "next/server"
import { requireControlCenterReadAccess } from "@/app/api/control-center/access"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"
import { readBoundedControlCenterMarkdownReport, ControlCenterMarkdownReportTooLargeError } from "@/lib/controlCenterMarkdownReportFile"
import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"

export const runtime = "nodejs"

export async function GET() {
  const access = await requireControlCenterReadAccess("Control Center release evidence report")
  if (!access.ok) return access.response

  const filePath = getControlCenterEvidenceConfig().evidenceMarkdownPath

  try {
    const body = await readBoundedControlCenterMarkdownReport(filePath)
    return new NextResponse(sanitizeControlCenterMarkdownReport(body), {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Cache-Control": "no-store",
      },
    })
  } catch (error) {
    if (error instanceof ControlCenterMarkdownReportTooLargeError) {
      return NextResponse.json({ error: "Evidence markdown is too large to display safely." }, { status: 413 })
    }
    return NextResponse.json({ error: "Evidence markdown not available yet." }, { status: 404 })
  }
}
