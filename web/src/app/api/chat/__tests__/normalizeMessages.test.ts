import { describe, expect, it } from "vitest"
import { buildBackendChatPayload, normalizeMessages } from "../route"

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

  it("builds a backend payload from an explicit allowlist", () => {
    const payload = buildBackendChatPayload({
      messages: [{ role: "user", content: "hello" }],
      model: "small",
      route_mode: "large",
      temperature: 0.2,
      debug_route: true,
      quality_retry: false,
      max_tokens: 999999,
      token: "should-not-forward",
    })

    expect(payload).toMatchObject({
      model: "small",
      route_mode: "large",
      temperature: 0.2,
    })
    expect(payload.messages[0].role).toBe("system")
    expect(payload.messages[1]).toEqual({ role: "user", content: "hello" })
    expect(payload).not.toHaveProperty("debug_route")
    expect(payload).not.toHaveProperty("quality_retry")
    expect(payload).not.toHaveProperty("max_tokens")
    expect(payload).not.toHaveProperty("token")
  })

  it("drops unsupported model routing and temperature values", () => {
    expect(
      buildBackendChatPayload({
        messages: [{ role: "user", content: "hello" }],
        model: "expensive-custom-model",
        route_mode: "debug",
        temperature: 7,
      }),
    ).toEqual({
      messages: expect.any(Array),
    })
  })
})
