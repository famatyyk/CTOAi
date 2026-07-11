export function redactControlCenterAuditText(value: string, maxLength = 1200): string {
  const redacted = String(value || "")
    .replace(/\b(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}/gi, "$1[redacted]")
    .replace(/\b(Basic\s+)[A-Za-z0-9+/=]{12,}/gi, "$1[redacted]")
    .replace(
      /\b(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|glpat-[A-Za-z0-9_-]{12,})\b/g,
      "[redacted]",
    )
    .replace(
      /\b((?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|token|secret|password|passwd|pwd|authorization|pgpassword)\s*[:=]\s*)([^&\s"'`,;}\]]{4,})/gi,
      "$1[redacted]",
    )
    .replace(
      /\b((?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|token|secret|password|passwd|pwd|authorization|pgpassword)["']?\s*[:=]\s*["'])([^"'\r\n]{4,})(["'])/gi,
      "$1[redacted]$3",
    )
    .trim()

  return redacted.length > maxLength ? redacted.slice(0, maxLength) : redacted
}

export function sanitizeControlCenterDisplayText(value: string, maxLength: number): string {
  const cleaned = redactControlCenterAuditText(value, Number.MAX_SAFE_INTEGER)
    .replace(/\s+/g, " ")
    .trim()
  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength - 1)}…` : cleaned
}
