import { afterEach, describe, expect, it, vi } from "vitest"
import { mkdtemp, rm, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { sanitizeControlCenterMarkdownReport } from "../controlCenterMarkdownReport"
import {
  ControlCenterMarkdownReportUnsafePathError,
  readBoundedControlCenterMarkdownReport,
} from "../controlCenterMarkdownReportFile"

const originalRepoRoot = process.env.CTOA_REPO_ROOT

afterEach(() => {
  if (originalRepoRoot === undefined) {
    delete process.env.CTOA_REPO_ROOT
  } else {
    process.env.CTOA_REPO_ROOT = originalRepoRoot
  }
  vi.unstubAllEnvs()
})

describe("Control Center markdown report sanitization", () => {
  it("redacts secrets and hides external absolute Windows paths", () => {
    vi.stubEnv("CTOA_REPO_ROOT", "C:\\repo\\CTOAi")

    const sanitized = sanitizeControlCenterMarkdownReport(
      [
        "# Evidence",
        "Live client: C:\\Users\\zycie\\AppData\\Local\\Solteria\\client",
        "Runtime JSON: C:\\repo\\CTOAi\\runtime\\evidence\\latest.json.",
        'Auth: {"access_token":"json-token-value"} password=legacy-password-value',
      ].join("\n"),
    )

    expect(sanitized).toContain("[external]/client")
    expect(sanitized).toContain("runtime/evidence/latest.json.")
    expect(sanitized).toContain('"access_token":"[redacted]"')
    expect(sanitized).toContain("password=[redacted]")
    expect(sanitized).not.toContain("C:\\Users\\zycie")
    expect(sanitized).not.toContain("C:\\repo\\CTOAi")
    expect(sanitized).not.toContain("json-token-value")
    expect(sanitized).not.toContain("legacy-password-value")
  })

  it("leaves non-path markdown content unchanged", () => {
    const body = "## Summary\nNo local paths here.\n"

    expect(sanitizeControlCenterMarkdownReport(body)).toBe(body)
  })

  it("keeps platform-local repo paths relative", () => {
    const repoRoot = path.join(path.parse(process.cwd()).root, "repo")
    vi.stubEnv("CTOA_REPO_ROOT", repoRoot)

    const localPath = path.join(repoRoot, "runtime", "api-cost", "latest.md")

    expect(sanitizeControlCenterMarkdownReport(`Path: ${localPath}`)).toContain("runtime/api-cost/latest.md")
  })

  it("redacts POSIX absolute local paths without rewriting API routes", () => {
    vi.stubEnv("CTOA_REPO_ROOT", "/repo/CTOAi")

    const sanitized = sanitizeControlCenterMarkdownReport(
      [
        "Runtime: /repo/CTOAi/runtime/evidence/latest.json.",
        "External temp: /tmp/ctoa/live/client)",
        'JSON path: {"path":"/home/runner/work/CTOAi/secret-output.json"}',
        "Route: /api/control-center/actions",
      ].join("\n"),
    )

    expect(sanitized).toContain("runtime/evidence/latest.json.")
    expect(sanitized).toContain("[external]/client)")
    expect(sanitized).toContain('"path":"[external]/secret-output.json"')
    expect(sanitized).toContain("Route: /api/control-center/actions")
    expect(sanitized).not.toContain("/repo/CTOAi")
    expect(sanitized).not.toContain("/tmp/ctoa")
    expect(sanitized).not.toContain("/home/runner")
  })
})

describe("Control Center markdown report file reads", () => {
  it("rejects symlinked report paths before following the target", async () => {
    const tempDir = await mkdtemp(path.join(os.tmpdir(), "ctoa-markdown-report-"))

    try {
      const targetPath = path.join(tempDir, "outside-report.md")
      const linkPath = path.join(tempDir, "latest.md")
      await writeFile(targetPath, "x".repeat(2048), "utf-8")

      try {
        await symlink(targetPath, linkPath)
      } catch {
        return
      }

      await expect(readBoundedControlCenterMarkdownReport(linkPath, 32)).rejects.toBeInstanceOf(
        ControlCenterMarkdownReportUnsafePathError,
      )
    } finally {
      await rm(tempDir, { recursive: true, force: true })
    }
  })
})
