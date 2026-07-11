import { beforeEach, describe, expect, it, vi } from "vitest"

const runControlCenterActionMock = vi.hoisted(() => vi.fn())
const resolveControlCenterViewerMock = vi.hoisted(() => vi.fn())
const listControlCenterActionsMock = vi.hoisted(() => vi.fn())

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: () => ({ value: "session-token" }),
  }),
}))

vi.mock("@/lib/config", () => ({
  getServerApiUrl: () => "http://localhost:8000",
}))

vi.mock("@/lib/controlCenterAuth", () => ({
  resolveControlCenterViewer: resolveControlCenterViewerMock,
}))

vi.mock("@/lib/controlCenterActions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/controlCenterActions")>("@/lib/controlCenterActions")
  return {
    ...actual,
    listControlCenterActions: listControlCenterActionsMock,
    runControlCenterAction: runControlCenterActionMock,
  }
})

function actionRequest(
  headers: HeadersInit,
  body: Record<string, unknown> = { actionId: "evidence-pack-refresh", dryRun: true },
) {
  return new Request("http://localhost/api/control-center/actions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  })
}

describe("control center action route origin guard", () => {
  beforeEach(() => {
    runControlCenterActionMock.mockReset()
    resolveControlCenterViewerMock.mockReset()
    listControlCenterActionsMock.mockReset()
    resolveControlCenterViewerMock.mockResolvedValue({
      authStatus: "authenticated",
      viewer: { username: "operator", displayName: "Operator", role: "operator" },
    })
    listControlCenterActionsMock.mockReturnValue([
      {
        id: "repo-hygiene-refresh",
        label: "Refresh repo hygiene snapshot",
        description: "Rebuild repo hygiene.",
        target: "local",
        riskClass: "safe_write",
        minimumRole: "operator",
        requiresReason: false,
        dryRunAvailable: true,
        enabled: true,
        commandSummary: "python scripts/ops/repo_hygiene_audit.py",
      },
      {
        id: "dangerous-maintenance",
        label: "Dangerous maintenance",
        description: "Owner-only maintenance.",
        target: "local",
        riskClass: "dangerous",
        minimumRole: "owner",
        requiresReason: true,
        dryRunAvailable: true,
        enabled: true,
        commandSummary: "python scripts/ops/private_maintenance.py --token=secret-token-value",
      },
    ])
  })

  it("does not expose the local action catalog to unauthenticated viewers", async () => {
    resolveControlCenterViewerMock.mockResolvedValue({
      authStatus: "unauthenticated",
      viewer: null,
    })
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.authStatus).toBe("unauthenticated")
    expect(payload.viewer).toBeNull()
    expect(payload.actions).toEqual([])
    expect(JSON.stringify(payload)).not.toContain("repo_hygiene_audit.py")
    expect(JSON.stringify(payload)).not.toContain("secret-token-value")
  })

  it("returns only actions allowed for the viewer role", async () => {
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.authStatus).toBe("authenticated")
    expect(payload.viewer.role).toBe("operator")
    expect(payload.actions.map((action: { id: string }) => action.id)).toEqual(["repo-hygiene-refresh"])
    expect(JSON.stringify(payload)).not.toContain("private_maintenance.py")
    expect(JSON.stringify(payload)).not.toContain("secret-token-value")
  })

  it("rejects cross-site POST requests before action execution", async () => {
    const { POST } = await import("./route")

    const response = await POST(actionRequest({ Origin: "https://attacker.example" }))
    const payload = await response.json()

    expect(response.status).toBe(403)
    expect(payload.error).toMatch(/Cross-site/)
    expect(runControlCenterActionMock).not.toHaveBeenCalled()
  })

  it("rejects cross-site fetch metadata without requiring an Origin header", async () => {
    const { POST } = await import("./route")

    const response = await POST(actionRequest({ "Sec-Fetch-Site": "cross-site" }))

    expect(response.status).toBe(403)
    expect(runControlCenterActionMock).not.toHaveBeenCalled()
  })

  it("validates same-origin Origin and Referer headers", async () => {
    const { validateControlCenterActionRequestOrigin } = await import("./route")

    expect(validateControlCenterActionRequestOrigin(actionRequest({ Origin: "http://localhost" }))).toEqual({
      ok: true,
    })
    expect(
      validateControlCenterActionRequestOrigin(
        actionRequest({ Referer: "http://localhost/control-center?tab=actions" }),
      ),
    ).toEqual({ ok: true })
    expect(validateControlCenterActionRequestOrigin(actionRequest({ Referer: "https://attacker.example/x" }))).toEqual({
      ok: false,
      error: "Cross-site Control Center action requests are not allowed.",
    })
  })

  it("sanitizes generic action errors before returning JSON", async () => {
    runControlCenterActionMock.mockRejectedValue(
      new Error(
        [
          "Unknown Control Center action: token=secret-token-value",
          "C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
          "/tmp/ctoa/action-error/latest.json",
        ].join(" "),
      ),
    )
    const { POST } = await import("./route")

    const response = await POST(actionRequest({ Origin: "http://localhost" }, { actionId: "token=secret-token-value" }))
    const payload = await response.json()

    expect(response.status).toBe(400)
    expect(payload.error).toContain("token=[redacted]")
    expect(payload.error).toContain("[external]/client")
    expect(payload.error).toContain("[external]/latest.json")
    expect(payload.error).not.toContain("secret-token-value")
    expect(payload.error).not.toContain("C:\\Users\\zycie")
    expect(payload.error).not.toContain("/tmp/ctoa")
  })

  it("sanitizes authorization errors before returning JSON", async () => {
    const { ControlCenterAuthorizationError } = await import("@/lib/controlCenterActions")
    runControlCenterActionMock.mockRejectedValue(
      new ControlCenterAuthorizationError(
        "Bearer abcdefghijklmnopqrstuvwxyz denied for /home/runner/work/CTOAi/private-output.json",
        401,
      ),
    )
    const { POST } = await import("./route")

    const response = await POST(actionRequest({ Origin: "http://localhost" }))
    const payload = await response.json()

    expect(response.status).toBe(401)
    expect(payload.error).toContain("Bearer [redacted]")
    expect(payload.error).toContain("[external]/private-output.json")
    expect(payload.error).not.toContain("abcdefghijklmnopqrstuvwxyz")
    expect(payload.error).not.toContain("/home/runner")
  })
})
