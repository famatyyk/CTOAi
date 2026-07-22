import { afterEach, describe, expect, it } from "vitest"
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import {
  collectApiCostCapability,
  collectControlCenterAuditCapability,
  collectReleaseEvidenceCapability,
  collectRepoHygieneCapability,
} from "../controlCenterEvidenceAdapters"

const temporaryRoots: string[] = []

afterEach(async () => {
  await Promise.all(temporaryRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
})

async function temporaryRoot(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-capability-adapters-"))
  temporaryRoots.push(root)
  return root
}

describe("Control Center evidence adapters", () => {
  it("projects repo and cost evidence without source paths or prompt names", async () => {
    const root = await temporaryRoot()
    const qualityPath = path.join(root, "runtime", "repo-hygiene", "quality.json")
    const costPath = path.join(root, "runtime", "api-cost", "cost.json")
    await mkdir(path.dirname(qualityPath), { recursive: true })
    await mkdir(path.dirname(costPath), { recursive: true })
    await writeFile(
      qualityPath,
      JSON.stringify({ status: "PASS", finding_count: 2, summary: { private_count: 1, public_count: 0, review_count: 1 } }),
    )
    await writeFile(
      costPath,
      JSON.stringify({
        records_seen: 3,
        total_tokens: 1200,
        total_cost_usd: 1.25,
        anomalies: ["one"],
        eval_artifacts: {
          dataset_path: "private/prompt-name.jsonl",
          prompt_variants_dir: "private/prompts",
          dataset_cases: 4,
          prompt_variant_count: 2,
        },
      }),
    )

    const payload = {
      repo: await collectRepoHygieneCapability(qualityPath),
      cost: await collectApiCostCapability(costPath),
    }
    const serialized = JSON.stringify(payload)

    expect(payload.repo).toMatchObject({ status: "ready", findingCount: 2 })
    expect(payload.cost).toMatchObject({ status: "ready", recordsSeen: 3, datasetCases: 4, promptVariantCount: 2 })
    expect(serialized).not.toContain(root)
    expect(serialized).not.toContain("prompt-name")
  })

  it("summarizes audits without identity, ids, reasons, or output", async () => {
    const root = await temporaryRoot()
    const auditPath = path.join(root, "runtime", "control-center", "action-audit.jsonl")
    await mkdir(path.dirname(auditPath), { recursive: true })
    await writeFile(
      auditPath,
      `${JSON.stringify({
        at: "2026-07-21T12:00:00Z",
        audit_id: "audit-private-42",
        actor: "private-user",
        actor_role: "operator",
        action: "evidence-pack-refresh",
        target: "C:/private/target",
        risk_class: "safe_write",
        dry_run: true,
        authorized: true,
        ok: true,
        reason: "private reason",
        output_preview: "private output",
      })}\n`,
    )

    const audit = await collectControlCenterAuditCapability(auditPath)
    const serialized = JSON.stringify(audit)

    expect(audit).toMatchObject({ status: "ready", recordCount: 1, dryRunCount: 1, authorizedCount: 1 })
    expect(audit.outcomes[0]).toEqual({
      action: "evidence-pack-refresh",
      riskClass: "safe_write",
      outcome: "dry-run; completed; authorized",
      dryRun: true,
      authorized: true,
    })
    expect(serialized).not.toContain("private-user")
    expect(serialized).not.toContain("audit-private-42")
    expect(serialized).not.toContain("private reason")
    expect(serialized).not.toContain("private output")
    expect(serialized).not.toContain("C:/private")
  })

  it("uses a path-free bounded projection for release evidence", async () => {
    const root = await temporaryRoot()
    const releases = path.join(root, "releases", "evidence")
    const sprint = path.join(releases, "sprint-private")
    await mkdir(sprint, { recursive: true })
    await writeFile(path.join(sprint, "private-prompt-name.md"), "# private evidence\n")

    const release = await collectReleaseEvidenceCapability(releases)
    const serialized = JSON.stringify(release)

    expect(release).toMatchObject({ status: "ready", sprintCount: 1, fileCount: 1, latestSprint: "sprint-private" })
    expect(serialized).not.toContain(root)
    expect(serialized).not.toContain("private-prompt-name")
  })
})
