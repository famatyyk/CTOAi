import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60;
export const dynamic = "force-dynamic";

const API_URL = process.env.VPS_API_URL ?? "http://116.202.96.250:8001";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const r = await fetch(API_URL + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(55000),
  });
  const data = await r.json();
  return NextResponse.json(data);
}
