import { describe, expect, it } from "vitest"
import { resolveControlCenterViewer } from "../controlCenterAuth"

describe("resolveControlCenterViewer", () => {
  it("returns unauthenticated when no token is present", async () => {
    const result = await resolveControlCenterViewer(undefined, "http://api.test", async () => {
      throw new Error("should not call fetch")
    })

    expect(result).toEqual({ viewer: null, authStatus: "unauthenticated" })
  })

  it("returns a viewer when auth me succeeds", async () => {
    const result = await resolveControlCenterViewer("token-123", "http://api.test", async () => {
      return new Response(
        JSON.stringify({
          user: {
            username: "famatyyk",
            display_name: "Famatyyk",
            role: "owner",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      )
    })

    expect(result).toEqual({
      viewer: {
        username: "famatyyk",
        displayName: "Famatyyk",
        role: "owner",
      },
      authStatus: "authenticated",
    })
  })

  it("treats unauthorized tokens as unauthenticated", async () => {
    const result = await resolveControlCenterViewer("token-123", "http://api.test", async () => {
      return new Response(JSON.stringify({ detail: "Missing bearer token" }), { status: 401 })
    })

    expect(result).toEqual({ viewer: null, authStatus: "unauthenticated" })
  })
})
