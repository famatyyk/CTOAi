import { sanitizeControlCenterMarkdownReport } from "@/lib/controlCenterMarkdownReport"

const SENSITIVE_AUTH_RESPONSE_KEYS = new Set([
  "access_token",
  "api_key",
  "auth_token",
  "authorization",
  "password",
  "passwd",
  "pwd",
  "refresh_token",
  "secret",
  "token",
])

export function sanitizeAuthProxyPayload(value: unknown): unknown {
  if (typeof value === "string") {
    return sanitizeControlCenterMarkdownReport(value)
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeAuthProxyPayload(item))
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => !SENSITIVE_AUTH_RESPONSE_KEYS.has(key.toLowerCase()))
        .map(([key, item]) => [key, sanitizeAuthProxyPayload(item)]),
    )
  }
  return value
}

export function authProxyCookieToken(value: unknown): string {
  if (!value || typeof value !== "object") {
    return ""
  }
  const token = (value as { token?: unknown }).token
  return typeof token === "string" ? token : ""
}
