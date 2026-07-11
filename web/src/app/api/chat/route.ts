import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"
import { SAFETY_SYSTEM_MESSAGE } from "@/lib/chatPolicy"
import { getServerApiUrl } from "@/lib/config"
import { createIpRateLimiter, getClientIp } from "@/lib/rateLimit"
import { assessControlCenterChatQuality } from "@/lib/chatQuality"
import { validateSameOriginRequest } from "@/lib/requestOriginGuard"
import { CTOA_TOKEN_COOKIE_NAME } from "@/lib/authCookies"

export const maxDuration = 60
export const dynamic = "force-dynamic"

const API_URL = getServerApiUrl()
const CHAT_MAX_MESSAGES = 40
const CHAT_MAX_MESSAGE_CHARS = 4000
const CHAT_RATE_LIMIT_PER_MIN = 24
const CHAT_RATE_WINDOW_MS = 60_000
const ALLOWED_MODEL_MODES = new Set(["auto", "small", "large"])

const consumeChatRateWindow = createIpRateLimiter(CHAT_RATE_LIMIT_PER_MIN, CHAT_RATE_WINDOW_MS)

type ChatRole = "user" | "assistant" | "system"

type ChatMessage = {
  role: ChatRole
  content: string
}


export function normalizeMessages(messages: unknown): ChatMessage[] {
  if (!Array.isArray(messages)) return []

  return messages
    .filter(
      (m): m is ChatMessage =>
        Boolean(m) &&
        typeof m === "object" &&
        ((m as { role?: unknown }).role === "user" || (m as { role?: unknown }).role === "assistant") &&
        typeof (m as { content?: unknown }).content === "string",
    )
    .slice(-CHAT_MAX_MESSAGES)
    .map((m) => ({
      role: m.role as "user" | "assistant",
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

function prependSafetySystemMessage(messages: ChatMessage[]): ChatMessage[] {
  return [{ role: "system", content: SAFETY_SYSTEM_MESSAGE }, ...messages]
}

export function buildBackendChatPayload(body: unknown) {
  const source = typeof body === "object" && body !== null ? (body as Record<string, unknown>) : {}
  const payload: {
    messages: ChatMessage[]
    model?: string
    route_mode?: string
    temperature?: number
  } = {
    messages: prependSafetySystemMessage(normalizeMessages(source.messages)),
  }

  if (typeof source.model === "string" && ALLOWED_MODEL_MODES.has(source.model)) {
    payload.model = source.model
  }
  if (typeof source.route_mode === "string" && ALLOWED_MODEL_MODES.has(source.route_mode)) {
    payload.route_mode = source.route_mode
  }
  if (typeof source.temperature === "number" && Number.isFinite(source.temperature) && source.temperature >= 0 && source.temperature <= 1) {
    payload.temperature = source.temperature
  }

  return payload
}

export function validateChatRequestOrigin(request: Request) {
  return validateSameOriginRequest(request, { requestLabel: "chat" })
}

export async function POST(req: NextRequest) {
  const originGate = validateChatRequestOrigin(req)
  if (!originGate.ok) {
    return NextResponse.json({ detail: originGate.error, code: "CROSS_SITE_REQUEST" }, { status: 403 })
  }

  const ip = getClientIp(req)
  const gate = consumeChatRateWindow(ip)
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
  const payload = buildBackendChatPayload(body)

  const token = (await cookies()).get(CTOA_TOKEN_COOKIE_NAME)?.value
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
      const safeContent = sanitizeAssistantContent(data.content)
      data.content = safeContent
      data.quality = assessControlCenterChatQuality(safeContent)
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
