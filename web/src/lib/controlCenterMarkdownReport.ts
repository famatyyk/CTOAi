import { toControlCenterDisplayPath } from "@/lib/controlCenterDisplayPath"
import { redactControlCenterAuditText } from "@/lib/controlCenterRedaction"

const WINDOWS_ABSOLUTE_PATH = /(?:\\\\\?\\)?[A-Za-z]:[\\/][^\s`"'<>|]+/g
const POSIX_ABSOLUTE_PATH =
  /(^|[\s(\[{"'`=:])\/(?:tmp|var|home|Users|opt|workspace|workspaces|mnt|private|repo|srv|root|builds|runner)(?:\/[^\s`"'<>|]+)*/g

export function sanitizeControlCenterMarkdownReport(value: string): string {
  const trailingNewlines = value.match(/\r?\n+$/)?.[0] || ""
  const sanitized = redactControlCenterAuditText(value, Number.MAX_SAFE_INTEGER)
    .replace(WINDOWS_ABSOLUTE_PATH, (match) => {
      const { pathValue, suffix } = trimPathSuffix(match)
      return `${toControlCenterDisplayPath(pathValue)}${suffix}`
    })
    .replace(POSIX_ABSOLUTE_PATH, (match, prefix: string) => {
      const pathMatch = match.slice(prefix.length)
      const { pathValue, suffix } = trimPathSuffix(pathMatch)
      return `${prefix}${toControlCenterDisplayPath(pathValue)}${suffix}`
    })
  return trailingNewlines && !sanitized.endsWith(trailingNewlines) ? `${sanitized}${trailingNewlines}` : sanitized
}

function trimPathSuffix(value: string): { pathValue: string; suffix: string } {
  let pathValue = value
  let suffix = ""
  while (/[.,;:)\]}]$/.test(pathValue)) {
    suffix = `${pathValue.slice(-1)}${suffix}`
    pathValue = pathValue.slice(0, -1)
  }
  return { pathValue, suffix }
}
