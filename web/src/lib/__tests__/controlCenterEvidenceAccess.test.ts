import { describe, expect, it } from "vitest"
import { authorizeControlCenterEvidenceAccess } from "../controlCenterEvidenceAccess"

describe("Control Center evidence access", () => {
  it("requires a signed-in operator for evidence reads", () => {
    expect(authorizeControlCenterEvidenceAccess({ viewer: null, authStatus: "unauthenticated" })).toMatchObject({
      ok: false,
      status: 401,
      body: {
        requiredRole: "operator",
        authStatus: "unauthenticated",
      },
    })

    expect(
      authorizeControlCenterEvidenceAccess({
        authStatus: "authenticated",
        viewer: { username: "member", displayName: "Member", role: "member" },
      }),
    ).toMatchObject({
      ok: false,
      status: 403,
      body: {
        requiredRole: "operator",
        authStatus: "authenticated",
      },
    })
  })

  it("allows operator and owner evidence reads", () => {
    expect(
      authorizeControlCenterEvidenceAccess({
        authStatus: "authenticated",
        viewer: { username: "operator", displayName: "Operator", role: "operator" },
      }),
    ).toMatchObject({ ok: true })

    expect(
      authorizeControlCenterEvidenceAccess({
        authStatus: "authenticated",
        viewer: { username: "owner", displayName: "Owner", role: "owner" },
      }),
    ).toMatchObject({ ok: true })
  })

  it("fails closed when auth status is invalid or unavailable", () => {
    expect(authorizeControlCenterEvidenceAccess({ viewer: null, authStatus: "invalid" })).toMatchObject({
      ok: false,
      status: 403,
    })
    expect(authorizeControlCenterEvidenceAccess({ viewer: null, authStatus: "unavailable" })).toMatchObject({
      ok: false,
      status: 503,
    })
  })
})
