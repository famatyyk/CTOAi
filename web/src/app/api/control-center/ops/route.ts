import { NextResponse } from "next/server"
import { collectControlCenterOps } from "@/lib/controlCenterOps"

export const runtime = "nodejs"

export async function GET() {
  const ops = await collectControlCenterOps()
  return NextResponse.json(ops)
}
