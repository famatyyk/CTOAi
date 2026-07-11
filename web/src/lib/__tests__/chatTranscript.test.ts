import { readFile } from "node:fs/promises"
import path from "node:path"
import { describe, expect, it } from "vitest"
import {
  buildControlCenterChatLog,
  buildControlCenterChatMarkdown,
  buildControlCenterChatMarkdownFileName,
  buildControlCenterChatTranscript,
  buildControlCenterChatTranscriptFileName,
  redactControlCenterChatMessages,
} from "../chatTranscript"

describe("chatTranscript helpers", () => {
  it("builds a readable transcript", () => {
    const transcript = buildControlCenterChatTranscript(
      [
        { role: "user", content: "hej" },
        { role: "assistant", content: "cześć", publicationState: "published" },
      ],
      {
        sessionId: "control-center-primary",
        viewerName: "Famatyyk",
        viewerRole: "owner",
        strictReviewMode: true,
        generatedAt: "2026-07-01T00:00:00.000Z",
      },
    )

    expect(transcript).toContain("CTOAi Control Center Chat Transcript")
    expect(transcript).toContain("[USER] hej")
    expect(transcript).toContain("publication: published")
  })

  it("builds a safe export filename", () => {
    expect(buildControlCenterChatTranscriptFileName("control center", "2026-07-01T00:00:00.000Z")).toBe(
      "ctoa-chat-control-center-2026-07-01T00-00-00-000Z.txt",
    )
  })

  it("builds a markdown export", () => {
    const markdown = buildControlCenterChatMarkdown(
      [{ role: "assistant", content: "gotowe", publicationState: "published" }],
      {
        sessionId: "control-center-primary",
        generatedAt: "2026-07-01T00:00:00.000Z",
        strictReviewMode: true,
      },
    )

    expect(markdown).toContain("# CTOAi Control Center Chat Transcript")
    expect(markdown).toContain("```text")
    expect(markdown).toContain("- Publication: `published`")
    expect(buildControlCenterChatMarkdownFileName("control center", "2026-07-01T00:00:00.000Z")).toBe(
      "ctoa-chat-control-center-2026-07-01T00-00-00-000Z.md",
    )
  })

  it("redacts secrets from persisted chat artifacts", () => {
    const messages = [
      {
        role: "user" as const,
        content:
          'please check Bearer abcdefghijklmnopqrstuvwxyz token=secret-token-value {"password":"json-password-value"}',
      },
      {
        role: "assistant" as const,
        content: "done sk-secret-should-not-leak",
        publicationState: "published" as const,
        publicationNote: "used api_key='quoted-api-key-value'",
        quality: {
          level: "review" as const,
          score: 62,
          issues: ["output included access_token=json-token-value"],
        },
      },
    ]

    const transcript = buildControlCenterChatTranscript(messages, {
      sessionId: "control-center-primary",
      generatedAt: "2026-07-01T00:00:00.000Z",
    })
    const markdown = buildControlCenterChatMarkdown(messages, {
      sessionId: "control-center-primary",
      generatedAt: "2026-07-01T00:00:00.000Z",
    })
    const log = buildControlCenterChatLog(messages, {
      sessionId: "control-center-primary",
      generatedAt: "2026-07-01T00:00:00.000Z",
    })
    const persisted = redactControlCenterChatMessages(messages)
    const combined = [transcript, markdown, JSON.stringify(log), JSON.stringify(persisted)].join("\n")

    expect(combined).toContain("Bearer [redacted]")
    expect(combined).toContain("token=[redacted]")
    expect(combined).toContain('"password":"[redacted]"')
    expect(combined).toContain("api_key='[redacted]'")
    expect(combined).toContain("access_token=[redacted]")
    expect(combined).not.toContain("secret-token-value")
    expect(combined).not.toContain("json-password-value")
    expect(combined).not.toContain("sk-secret-should-not-leak")
    expect(combined).not.toContain("quoted-api-key-value")
    expect(combined).not.toContain("json-token-value")
  })

  it("redacts messages before Control Center chat localStorage persistence", async () => {
    const source = await readFile(path.join(process.cwd(), "src/components/ControlCenterChatPanel.tsx"), "utf-8")

    expect(source).toContain("redactControlCenterChatMessages(messages).slice(-80)")
  })
})
