import { beforeEach, describe, expect, it, vi } from "vitest"

const requireControlCenterReadAccessMock = vi.hoisted(() => vi.fn())
const collectControlCenterEvidenceMock = vi.hoisted(() => vi.fn())
const collectControlCenterOpsMock = vi.hoisted(() => vi.fn())
const lstatMock = vi.hoisted(() => vi.fn())
const openMock = vi.hoisted(() => vi.fn())
const fileStatMock = vi.hoisted(() => vi.fn())
const fileReadMock = vi.hoisted(() => vi.fn())
const fileCloseMock = vi.hoisted(() => vi.fn())

vi.mock("@/app/api/control-center/access", () => ({
  requireControlCenterReadAccess: requireControlCenterReadAccessMock,
}))

vi.mock("@/lib/controlCenterEvidence", () => ({
  collectControlCenterEvidence: collectControlCenterEvidenceMock,
}))

vi.mock("@/lib/controlCenterOps", () => ({
  collectControlCenterOps: collectControlCenterOpsMock,
}))

vi.mock("@/lib/controlCenterEvidenceConfig", () => ({
  getControlCenterEvidenceConfig: () => ({
    evidenceMarkdownPath: "runtime/evidence/latest.md",
    apiCostMarkdownPath: "runtime/api-cost/latest.md",
  }),
}))

vi.mock("node:fs/promises", () => ({
  lstat: lstatMock,
  open: openMock,
}))

function denyAccess(status = 403) {
  return {
    ok: false,
    response: new Response(JSON.stringify({ ok: false, error: "denied" }), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  }
}

function allowAccess() {
  return {
    ok: true,
    viewer: { username: "operator", displayName: "Operator", role: "operator" },
  }
}

function mockMarkdownFile(contents: string) {
  const bytes = Buffer.from(contents, "utf-8")
  lstatMock.mockResolvedValue({ isFile: () => true, isSymbolicLink: () => false, size: bytes.length })
  fileStatMock.mockResolvedValue({ isFile: () => true, size: bytes.length })
  fileReadMock.mockImplementation(async (target: Buffer, offset: number, length: number, position: number) => {
    const start = position || 0
    const bytesRead = Math.min(length, Math.max(0, bytes.length - start))
    bytes.copy(target, offset, start, start + bytesRead)
    return { bytesRead, buffer: target }
  })
  openMock.mockResolvedValue({
    stat: fileStatMock,
    read: fileReadMock,
    close: fileCloseMock,
  })
}

describe("Control Center evidence routes", () => {
  beforeEach(() => {
    requireControlCenterReadAccessMock.mockReset()
    collectControlCenterEvidenceMock.mockReset()
    collectControlCenterOpsMock.mockReset()
    lstatMock.mockReset()
    openMock.mockReset()
    fileStatMock.mockReset()
    fileReadMock.mockReset()
    fileCloseMock.mockReset()
    mockMarkdownFile("# Ready\n")
    requireControlCenterReadAccessMock.mockResolvedValue(allowAccess())
  })

  it("requires operator access before collecting evidence JSON", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess(401))
    const { GET } = await import("./route")

    const response = await GET()

    expect(response.status).toBe(401)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center evidence")
    expect(collectControlCenterEvidenceMock).not.toHaveBeenCalled()
  })

  it("returns evidence JSON after access is granted", async () => {
    collectControlCenterEvidenceMock.mockResolvedValue({ status: "ready" })
    const { GET } = await import("./route")

    const response = await GET()

    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ status: "ready" })
  })

  it("returns P7 cockpit fields in authenticated evidence JSON", async () => {
    collectControlCenterEvidenceMock.mockResolvedValue({
      engineBrain: {
        status: "ready",
        p6ReadinessStatus: "ready_for_plugin_design",
        p7OperatorBriefStatus: "ready",
        p7Decision: "ready_for_p7_operator_workflow",
        p7ActionReadinessStatus: "safe_write_tools_enabled",
        p7SafeWriteToolDesignStatus: "implemented",
        p7EnabledSafeWriteToolCount: 5,
        p7ReadySafeWriteAuditCount: 5,
        p7SafeWriteAuditCount: 5,
        p7OperatorCockpitSummary: "5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.",
        sourcePaths: {
          operatorBrief: "AI/generated/P7_OPERATOR_BRIEF.json",
        },
      },
      operatorBrief: {
        status: "ready",
        ready: true,
        cockpitHandoff: {
          status: "ready",
          ready: true,
          p7CockpitSmoke: { status: "ready", checks: 14, passed: 14 },
          releaseEvidence: { status: "ready", fileCount: 35 },
          actionAudit: { status: "ready", recordCount: 42 },
        },
      },
    })
    const { GET } = await import("./route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.engineBrain).toMatchObject({
      status: "ready",
      p6ReadinessStatus: "ready_for_plugin_design",
      p7OperatorBriefStatus: "ready",
      p7Decision: "ready_for_p7_operator_workflow",
      p7ActionReadinessStatus: "safe_write_tools_enabled",
      p7SafeWriteToolDesignStatus: "implemented",
      p7EnabledSafeWriteToolCount: 5,
      p7ReadySafeWriteAuditCount: 5,
      p7SafeWriteAuditCount: 5,
      p7OperatorCockpitSummary: "5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.",
    })
    expect(payload.engineBrain.sourcePaths.operatorBrief).toBe("AI/generated/P7_OPERATOR_BRIEF.json")
    expect(payload.operatorBrief).toMatchObject({
      status: "ready",
      ready: true,
      cockpitHandoff: {
        status: "ready",
        ready: true,
        p7CockpitSmoke: { status: "ready", checks: 14, passed: 14 },
        releaseEvidence: { status: "ready", fileCount: 35 },
        actionAudit: { status: "ready", recordCount: 42 },
      },
    })
  })

  it("requires operator access before collecting ops evidence", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess(403))
    const { GET } = await import("../ops/route")

    const response = await GET()

    expect(response.status).toBe(403)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center ops evidence")
    expect(collectControlCenterOpsMock).not.toHaveBeenCalled()
  })

  it("returns P7 cockpit fields in authenticated ops JSON", async () => {
    collectControlCenterOpsMock.mockResolvedValue({
      details: {
        engineBrain: {
          status: "ready",
          p7OperatorBriefStatus: "ready",
          p7Decision: "ready_for_p7_operator_workflow",
          p7ActionReadinessStatus: "safe_write_tools_enabled",
          p7SafeWriteToolDesignStatus: "implemented",
          p7EnabledSafeWriteToolCount: 5,
          p7ReadySafeWriteAuditCount: 5,
          p7SafeWriteAuditCount: 5,
          p7OperatorCockpitSummary: "5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.",
        },
      },
    })
    const { GET } = await import("../ops/route")

    const response = await GET()
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.details.engineBrain).toMatchObject({
      status: "ready",
      p7OperatorBriefStatus: "ready",
      p7Decision: "ready_for_p7_operator_workflow",
      p7ActionReadinessStatus: "safe_write_tools_enabled",
      p7SafeWriteToolDesignStatus: "implemented",
      p7EnabledSafeWriteToolCount: 5,
      p7ReadySafeWriteAuditCount: 5,
      p7SafeWriteAuditCount: 5,
      p7OperatorCockpitSummary: "5 enabled safe-write MCP tools; 5/5 audits ready; 5 MCP write tools declared.",
    })
  })

  it("requires operator access before reading release evidence markdown", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess(403))
    const { GET } = await import("./report/route")

    const response = await GET()

    expect(response.status).toBe(403)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center release evidence report")
    expect(openMock).not.toHaveBeenCalled()
  })

  it("requires operator access before reading API cost markdown", async () => {
    requireControlCenterReadAccessMock.mockResolvedValue(denyAccess(403))
    const { GET } = await import("./api-cost-report/route")

    const response = await GET()

    expect(response.status).toBe(403)
    expect(requireControlCenterReadAccessMock).toHaveBeenCalledWith("Control Center API cost report")
    expect(openMock).not.toHaveBeenCalled()
  })

  it("returns sanitized markdown report content after access is granted", async () => {
    mockMarkdownFile(
      [
        "# Evidence",
        "Live client: C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
        'Token: {"access_token":"json-token-value"} password=legacy-password-value',
      ].join("\n"),
    )
    const { GET } = await import("./report/route")

    const response = await GET()
    const body = await response.text()

    expect(response.status).toBe(200)
    expect(response.headers.get("Content-Type")).toContain("text/markdown")
    expect(lstatMock).toHaveBeenCalledWith("runtime/evidence/latest.md")
    expect(openMock).toHaveBeenCalledWith("runtime/evidence/latest.md", "r")
    expect(fileReadMock).toHaveBeenCalled()
    expect(fileCloseMock).toHaveBeenCalled()
    expect(body).toContain("[external]/client")
    expect(body).toContain('"access_token":"[redacted]"')
    expect(body).toContain("password=[redacted]")
    expect(body).not.toContain("C:\\Users\\zycie")
    expect(body).not.toContain("json-token-value")
    expect(body).not.toContain("legacy-password-value")
  })

  it("rejects symlinked markdown report paths before opening them", async () => {
    lstatMock.mockResolvedValue({ isFile: () => false, isSymbolicLink: () => true, size: 1024 * 1024 + 1 })
    const { GET } = await import("./report/route")

    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(404)
    expect(body.error).toBe("Evidence markdown not available yet.")
    expect(openMock).not.toHaveBeenCalled()
    expect(fileReadMock).not.toHaveBeenCalled()
    expect(fileCloseMock).not.toHaveBeenCalled()
  })

  it("returns sanitized API cost markdown content after access is granted", async () => {
    mockMarkdownFile("Cost report path: C:\\Users\\zycie\\runtime\\api-cost\\latest.md")
    const { GET } = await import("./api-cost-report/route")

    const response = await GET()
    const body = await response.text()

    expect(response.status).toBe(200)
    expect(response.headers.get("Content-Type")).toContain("text/markdown")
    expect(openMock).toHaveBeenCalledWith("runtime/api-cost/latest.md", "r")
    expect(fileReadMock).toHaveBeenCalled()
    expect(fileCloseMock).toHaveBeenCalled()
    expect(body).toContain("[external]/latest.md")
    expect(body).not.toContain("C:\\Users\\zycie")
  })

  it("rejects oversized release evidence markdown from a bounded read", async () => {
    mockMarkdownFile("x".repeat(1024 * 1024 + 1))
    const { GET } = await import("./report/route")

    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(413)
    expect(body.error).toBe("Evidence markdown is too large to display safely.")
    expect(fileReadMock).toHaveBeenCalled()
    expect(fileCloseMock).toHaveBeenCalled()
  })

  it("rejects oversized API cost markdown from a bounded read", async () => {
    mockMarkdownFile("x".repeat(1024 * 1024 + 1))
    const { GET } = await import("./api-cost-report/route")

    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(413)
    expect(body.error).toBe("API cost markdown is too large to display safely.")
    expect(fileReadMock).toHaveBeenCalled()
    expect(fileCloseMock).toHaveBeenCalled()
  })
})
