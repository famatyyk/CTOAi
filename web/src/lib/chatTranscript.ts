import type { StoredMessage } from "@/lib/sessionStorage"
import { redactControlCenterAuditText } from "@/lib/controlCenterRedaction"

export type ChatTranscriptMetadata = {
  sessionId: string
  viewerName?: string | null
  viewerRole?: string | null
  strictReviewMode?: boolean
  generatedAt?: string
}

function redactChatText(value: string): string {
  return redactControlCenterAuditText(value, Number.MAX_SAFE_INTEGER)
}

export function redactControlCenterChatMessage(message: StoredMessage): StoredMessage {
  return {
    ...message,
    content: redactChatText(message.content),
    quality: message.quality
      ? {
          ...message.quality,
          issues: message.quality.issues.map(redactChatText),
        }
      : undefined,
    publicationNote: message.publicationNote ? redactChatText(message.publicationNote) : undefined,
  }
}

export function redactControlCenterChatMessages(messages: StoredMessage[]): StoredMessage[] {
  return messages.map(redactControlCenterChatMessage)
}

function formatMessage(message: StoredMessage): string {
  const safeMessage = redactControlCenterChatMessage(message)
  const lines = [`[${safeMessage.role.toUpperCase()}] ${safeMessage.content}`]
  if (safeMessage.quality) {
    lines.push(`  quality: ${safeMessage.quality.level} (${safeMessage.quality.score}/100)`)
    if (safeMessage.quality.issues.length > 0) {
      lines.push(`  issues: ${safeMessage.quality.issues.join(" | ")}`)
    }
  }
  if (safeMessage.publicationState) {
    lines.push(`  publication: ${safeMessage.publicationState}`)
  }
  if (safeMessage.publicationNote) {
    lines.push(`  note: ${safeMessage.publicationNote}`)
  }
  return lines.join("\n")
}

function escapeMarkdown(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/\*/g, "\\*").replace(/_/g, "\\_").replace(/`/g, "\\`")
}

function buildFence(content: string): string {
  const matches = content.match(/`+/g) || []
  const longest = matches.reduce((max, run) => Math.max(max, run.length), 0)
  return "`".repeat(Math.max(3, longest + 1))
}

export function buildControlCenterChatTranscript(messages: StoredMessage[], metadata: ChatTranscriptMetadata): string {
  const generatedAt = metadata.generatedAt || new Date().toISOString()
  const header = [
    "CTOAi Control Center Chat Transcript",
    `Session: ${metadata.sessionId}`,
    `Generated: ${generatedAt}`,
    metadata.viewerName ? `Viewer: ${metadata.viewerName}${metadata.viewerRole ? ` (${metadata.viewerRole})` : ""}` : null,
    typeof metadata.strictReviewMode === "boolean" ? `Mode: ${metadata.strictReviewMode ? "hard review" : "standard"}` : null,
  ].filter(Boolean)

  const body = messages.map(formatMessage).join("\n\n")
  return `${header.join("\n")}\n\n${body}\n`
}

export function buildControlCenterChatMarkdown(messages: StoredMessage[], metadata: ChatTranscriptMetadata): string {
  const generatedAt = metadata.generatedAt || new Date().toISOString()
  const lines = [
    "# CTOAi Control Center Chat Transcript",
    "",
    `- Session: \`${escapeMarkdown(metadata.sessionId)}\``,
    `- Generated: \`${escapeMarkdown(generatedAt)}\``,
    metadata.viewerName ? `- Viewer: ${escapeMarkdown(metadata.viewerName)}${metadata.viewerRole ? ` (${escapeMarkdown(metadata.viewerRole)})` : ""}` : null,
    typeof metadata.strictReviewMode === "boolean" ? `- Mode: ${metadata.strictReviewMode ? "hard review" : "standard"}` : null,
    "",
  ].filter(Boolean)

  for (const message of redactControlCenterChatMessages(messages)) {
    const fence = buildFence(message.content)
    lines.push(`## ${message.role === "user" ? "User" : "Assistant"}`)
    lines.push("")
    lines.push(`${fence}text`)
    lines.push(message.content)
    lines.push(fence)
    lines.push("")
    if (message.quality) {
      lines.push(`- Quality: \`${message.quality.level}\` (${message.quality.score}/100)`)
      if (message.quality.issues.length > 0) {
        lines.push(`- Issues: ${message.quality.issues.map((issue) => `\`${escapeMarkdown(issue)}\``).join(", ")}`)
      }
    }
    if (message.publicationState) {
      lines.push(`- Publication: \`${message.publicationState}\``)
    }
    if (message.publicationNote) {
      lines.push(`- Note: ${escapeMarkdown(message.publicationNote)}`)
    }
    lines.push("")
  }

  return lines.join("\n").trimEnd() + "\n"
}

export function buildControlCenterChatLog(messages: StoredMessage[], metadata: ChatTranscriptMetadata) {
  const generatedAt = metadata.generatedAt || new Date().toISOString()
  return {
    generatedAt,
    sessionId: metadata.sessionId,
    viewerName: metadata.viewerName || null,
    viewerRole: metadata.viewerRole || null,
    strictReviewMode: Boolean(metadata.strictReviewMode),
    messages: redactControlCenterChatMessages(messages),
  }
}

export function buildControlCenterChatTranscriptFileName(sessionId: string, generatedAt: string): string {
  const safeSession = sessionId.replace(/[^a-z0-9_-]+/gi, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "")
  const safeStamp = generatedAt.replace(/[:.]/g, "-")
  return `ctoa-chat-${safeSession}-${safeStamp}.txt`
}

export function buildControlCenterChatMarkdownFileName(sessionId: string, generatedAt: string): string {
  const safeSession = sessionId.replace(/[^a-z0-9_-]+/gi, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "")
  const safeStamp = generatedAt.replace(/[:.]/g, "-")
  return `ctoa-chat-${safeSession}-${safeStamp}.md`
}
