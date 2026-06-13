import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

export const maxDuration = 60
export const dynamic = "force-dynamic"

const API_URL = process.env.VPS_API_URL ?? "http://116.202.96.250:8001"
const CHAT_MAX_MESSAGES = 40
const CHAT_MAX_MESSAGE_CHARS = 4000
const CHAT_RATE_LIMIT_PER_MIN = 24
const CHAT_RATE_WINDOW_MS = 60_000

type RateWindow = {
  count: number
  resetAt: number
}

const chatIpWindows = new Map<string, RateWindow>()

const SAFETY_SYSTEM_MESSAGE =
  "Jestes CTOAi STRATEGOS - osobisty asystent CTO stworzony przez Jakuba P. (Famatyyk). " +
  "Odpowiadasz zawsze po polsku, jesli uzytkownik pisze po polsku. Po angielsku, jesli pisze po angielsku. " +
  "Piszesz pelne, poprawne zdania. Unikasz bzdurnych slow i skrotow bez kontekstu. " +
  "Jestes konkretny, techniczny i pomocny jak dobry CTO. " +
  "Nie twierdzisz ze wykonales akcje administracyjne bez realnego potwierdzenia z systemu." +
  "Odpowiadasz zawsze po polsku, jesli uzytkownik pisze po polsku. Po angielsku, jesli pisze po angielsku. " +
  "Piszesz pelne, poprawne gramatycznie zdania. Unikasz niepotrzebnych skrotow i bezdusznych odpowiedzi. " +
  "Jestes konkretny, techniczny i pomocny – jak dobry CTO. " +
  "Nie twierdzisz, ze wykonales akcje administracyjne bez realnego potwierdzenia. " +
  "Nie tworzysz kont, nie resetujesz hasel ani nie nadajesz uprawnien bez wyraznego potwierdzenia z systemu."

type ChatMessage = {
  role: string
  content: string
}


function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for")
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim()
    if (first) return first
  }
  const real = req.headers.get("x-real-ip")?.trim()
  return real || "unknown"
}

function consumeRateWindow(ip: string): { allowed: boolean; retryAfter: number } {
  const now = Date.now()
  const current = chatIpWindows.get(ip)
  if (!current || current.resetAt <= now) {
    chatIpWindows.set(ip, { count: 1, resetAt: now + CHAT_RATE_WINDOW_MS })
    return { allowed: true, retryAfter: 0 }
  }

  if (current.count >= CHAT_RATE_LIMIT_PER_MIN) {
    return { allowed: false, retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)) }
  }

  current.count += 1
  chatIpWindows.set(ip, current)
  return { allowed: true, retryAfter: 0 }
}

function normalizeMessages(messages: unknown): ChatMessage[] {
  if (!Array.isArray(messages)) return []

  return messages
    .filter(
      (m): m is ChatMessage =>
        Boolean(m) &&
        typeof m === "object" &&
        typeof (m as { role?: unknown }).role === "string" &&
        typeof (m as { content?: unknown }).content === "string",
    )
    .slice(-CHAT_MAX_MESSAGES)
    .map((m) => ({
      role: m.role,
      content: m.content.slice(0, CHAT_MAX_MESSAGE_CHARS),
    }))
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
  const ip = getClientIp(req)
  const gate = consumeRateWindow(ip)
  if (!gate.allowed) {
    return NextResponse.json(
      {
        detail: "Rate limit exceeded. Please retry shortly.",
        code: "RATE_LIMITED",
        retry_after: gate.retryAfter,
      },
      { status: 429, headers: { "Retry-After": String(gate.retryAfter) } },
    )
  }
  const body = await req.json().catch(() => ({}))
  const payload = {
    ...(typeof body === "object" && body !== null ? body : {}),
    messages: prependSafetySystemMessage(normalizeMessages((body as { messages?: unknown })?.messages)),
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

