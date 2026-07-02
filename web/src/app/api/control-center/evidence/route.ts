import { NextResponse } from "next/server"
import { collectControlCenterEvidence } from "@/lib/controlCenterEvidence"

export const runtime = "nodejs"

export async function GET() {
  const evidence = await collectControlCenterEvidence()
  return NextResponse.json(evidence)
}
