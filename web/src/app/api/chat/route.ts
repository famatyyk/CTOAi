import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

export const maxDuration = 60
export const dynamic = "force-dynamic"

const API_URL = process.env.VPS_API_URL ?? "http://116.202.96.250:8001"

const SAFETY_SYSTEM_MESSAGE =
  "Nigdy nie twierdz, ze wykonales akcje administracyjne, systemowe lub destrukcyjne bez realnego wykonania i dowodu. Nie odgrywaj tworzenia kont, resetu hasel, nadawania uprawnien ani samowylaczenia."

type ChatMessage = {
  role: string
  content: string
}

function toSafeError(status: number): { status: number; detail: string; code: string } {
  if (status === 429 || status === 503) {
    return {
      status: 503,
      detail: "Model jest chwilowo przeciazony. Sprobuj ponownie za chwile.",
      code: "MODEL_RATE_LIMIT",
    }
  }

  if (status >= 500) {
    return {
      status: 502,
      detail: "Backend modelu jest chwilowo niedostepny. Sprobuj ponownie za chwile.",
      code: "MODEL_BACKEND_UNAVAILABLE",
    }
  }

  return {
    status,
    detail: "Nie udalo sie przetworzyc zapytania.",
    code: "CHAT_REQUEST_FAILED",
  }
}

function sanitizeAssistantContent(content: string): string {
  const lowered = content.toLowerCase()
  const blocked = [
    "create-user",
    "set-password",
    "grant-permissions",
    "self-terminate",
    "wylaczam sie",
    "jestem juz wylaczony",
  ]

  if (blocked.some((marker) => lowered.includes(marker))) {
    return "Nie moge potwierdzac wykonania akcji administracyjnych lub systemowych bez realnego wykonania i dowodu."
  }

  return content
}

function prependSafetySystemMessage(messages: unknown): ChatMessage[] {
  const normalized = Array.isArray(messages)
    ? messages.filter(
        (m): m is ChatMessage =>
          Boolean(m) &&
          typeof m === "object" &&
          typeof (m as { role?: unknown }).role === "string" &&
          typeof (m as { content?: unknown }).content === "string",
      )
    : []

  return [{ role: "system", content: SAFETY_SYSTEM_MESSAGE }, ...normalized]
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const payload = {
    ...(typeof body === "object" && body !== null ? body : {}),
    messages: prependSafetySystemMessage((body as { messages?: unknown })?.messages),
  }

  const token = (await cookies()).get("ctoa_token")?.value
  const ctrl = new AbortController()
  let timeoutTriggered = false
  const timer = setTimeout(() => {
    timeoutTriggered = true
    ctrl.abort()
  }, 55000)

  try {
    const r = await fetch(API_URL + "/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    })

    const data = (await r.json().catch(() => ({}))) as Record<string, unknown>

    if (!r.ok) {
      const safe = toSafeError(r.status)
      return NextResponse.json({ detail: safe.detail, code: safe.code }, { status: safe.status })
    }

    if (typeof data.content === "string") {
      data.content = sanitizeAssistantContent(data.content)
    }

    return NextResponse.json(data, { status: r.status })
  } catch {
    if (timeoutTriggered) {
      return NextResponse.json(
        {
          detail: "Brak odpowiedzi z backendu modelu. Sprobuj ponownie za chwile.",
          code: "MODEL_TIMEOUT",
        },
        { status: 504 },
      )
    }

    return NextResponse.json(
      {
        detail: "Backend modelu jest chwilowo niedostepny. Sprobuj ponownie za chwile.",
        code: "MODEL_BACKEND_UNAVAILABLE",
      },
      { status: 502 },
    )
  } finally {
    clearTimeout(timer)
  }
}
