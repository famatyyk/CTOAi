import { afterEach, describe, expect, it, vi } from "vitest"
import path from "node:path"
import { toControlCenterDisplayConfig, toControlCenterDisplayPath } from "../controlCenterDisplayPath"

const originalRepoRoot = process.env.CTOA_REPO_ROOT

afterEach(() => {
  if (originalRepoRoot === undefined) {
    delete process.env.CTOA_REPO_ROOT
  } else {
    process.env.CTOA_REPO_ROOT = originalRepoRoot
  }
  vi.unstubAllEnvs()
})

describe("Control Center display paths", () => {
  it("keeps repo-local paths relative for UI evidence", () => {
    const repoRoot = path.join(path.parse(process.cwd()).root, "repo")
    vi.stubEnv("CTOA_REPO_ROOT", repoRoot)

    expect(toControlCenterDisplayPath(path.join(repoRoot, "runtime", "evidence", "latest.json"))).toBe(
      "runtime/evidence/latest.json",
    )
    expect(toControlCenterDisplayPath("runtime/evidence/latest.json")).toBe("runtime/evidence/latest.json")
  })

  it("hides external absolute parent directories", () => {
    const repoRoot = path.join(path.parse(process.cwd()).root, "repo")
    const externalRoot = path.join(path.parse(process.cwd()).root, "Users", "zycie", "secret-runtime")
    vi.stubEnv("CTOA_REPO_ROOT", repoRoot)

    expect(toControlCenterDisplayPath(path.join(externalRoot, "latest.json"))).toBe("[external]/latest.json")
  })

  it("sanitizes all string values in evidence config", () => {
    const repoRoot = path.join(path.parse(process.cwd()).root, "repo")
    vi.stubEnv("CTOA_REPO_ROOT", repoRoot)

    expect(
      toControlCenterDisplayConfig({
        evidenceJsonPath: path.join(repoRoot, "runtime", "evidence", "latest.json"),
        liveClient: path.join(path.parse(process.cwd()).root, "Users", "zycie", "AppData", "Local", "client"),
      }),
    ).toEqual({
      evidenceJsonPath: "runtime/evidence/latest.json",
      liveClient: "[external]/client",
    })
  })
})
