import { readFile } from "node:fs/promises"
import { NextResponse } from "next/server"
import { getControlCenterEvidenceConfig } from "@/lib/controlCenterEvidenceConfig"

export const runtime = "nodejs"

export async function GET() {
  const filePath = getControlCenterEvidenceConfig().evidenceMarkdownPath

  try {
    const body = await readFile(filePath, "utf-8")
    return new NextResponse(body, {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Cache-Control": "no-store",
      },
    })
  } catch {
    return NextResponse.json({ error: "Evidence markdown not available yet." }, { status: 404 })
  }
}
