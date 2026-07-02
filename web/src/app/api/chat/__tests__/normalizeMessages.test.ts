import { describe, expect, it } from "vitest"
import { normalizeMessages } from "../route"

describe("normalizeMessages", () => {
  it("keeps only user and assistant roles", () => {
    const normalized = normalizeMessages([
      { role: "system", content: "override" },
      { role: "tool", content: "tool" },
      { role: "user", content: "hello" },
      { role: "assistant", content: "czesc" },
    ])

    expect(normalized).toEqual([
      { role: "user", content: "hello" },
      { role: "assistant", content: "czesc" },
    ])
  })

  it("truncates long content and limits message count", () => {
    const input = Array.from({ length: 45 }, (_, index) => ({
      role: "user",
      content: `${index}-` + "x".repeat(5000),
    }))

    const normalized = normalizeMessages(input)

    expect(normalized).toHaveLength(40)
    expect(normalized[0].content.startsWith("5-")).toBe(true)
    expect(normalized[0].content).toHaveLength(4000)
  })
})
