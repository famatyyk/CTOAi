import { describe, expect, it } from "vitest"
import {
  buildControlCenterChatMarkdown,
  buildControlCenterChatMarkdownFileName,
  buildControlCenterChatTranscript,
  buildControlCenterChatTranscriptFileName,
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
})
