import os from "node:os"
import path from "node:path"
import { mkdtemp, rm, writeFile } from "node:fs/promises"
import { afterEach, describe, expect, it } from "vitest"
import {
  getClientCapabilities,
  getClients,
  getDiffLedger,
  getLatestUpdates,
  getTibiaSources,
  validateConfigDryRun,
} from "../tibiaOperationalState"

describe("Tibia operational state contract", () => {
  const originalClientStatePath = process.env.CTOA_HELPER_CLIENT_STATE_PATH
  const originalArchiveDir = process.env.CTOA_TIBIA_SOURCE_ARCHIVE_DIR
  const temporaryRoots: string[] = []

  afterEach(async () => {
    if (originalClientStatePath === undefined) delete process.env.CTOA_HELPER_CLIENT_STATE_PATH
    else process.env.CTOA_HELPER_CLIENT_STATE_PATH = originalClientStatePath
    if (originalArchiveDir === undefined) delete process.env.CTOA_TIBIA_SOURCE_ARCHIVE_DIR
    else process.env.CTOA_TIBIA_SOURCE_ARCHIVE_DIR = originalArchiveDir
    await Promise.all(temporaryRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })))
  })

  it("reports explicit source states without fake freshness", async () => {
    const payload = await getTibiaSources()

    expect(payload.mode).toBe("local_contract")
    expect(payload.states).toContain("source_blocked")
    expect(payload.states).toContain("parser_broken")
    expect(payload.states).toContain("stale_snapshot")
    expect(payload.sources.some((source) => source.status === "source_blocked")).toBe(true)
    expect(payload.sources.every((source) => source.raw_snapshot.content_hash === null)).toBe(true)
  })

  it("keeps Summer Update protocol work pending until real sources exist", async () => {
    const updates = await getLatestUpdates()
    const protocolEvent = updates.events.find((event) => event.event_id === "protocol-summer-2026-pending")

    expect(protocolEvent?.payload.status).toBe("pending_protocol_source")
    expect(protocolEvent?.payload.modules).toEqual(["weapon_proficiency", "boss_difficulty", "monk_virtues"])
  })

  it("returns a stale diff ledger for surfaces with no archived events", async () => {
    expect((await getDiffLedger("library")).status).toBe("stale_snapshot")
    expect((await getDiffLedger("news")).status).toBe("source_blocked")
  })

  it("reads archived source evidence and its diff ledger instead of contract placeholders", async () => {
    const archiveDir = await mkdtemp(path.join(os.tmpdir(), "ctoa-tibia-archive-"))
    temporaryRoots.push(archiveDir)
    await writeFile(
      path.join(archiveDir, "source-index.json"),
      JSON.stringify({
        schema_version: "ctoa-tibia-source-archive-v1",
        generated_at: "2026-07-09T12:00:00.000Z",
        sources: {
          news: {
            source_kind: "news",
            label: "Tibia.com News",
            url: "https://www.tibia.com/news/",
            status: "fresh",
            freshness: "live",
            raw_snapshot: {
              source_kind: "news",
              fetched_at: "2026-07-09T12:00:00.000Z",
              url: "https://www.tibia.com/news/",
              content_hash: "a".repeat(64),
              blocked_reason: null,
            },
            parser: {
              status: "ready",
              normalized_kinds: ["news/security", "news/fixes"],
              last_error: null,
            },
            next_action: "Poll again on the configured interval.",
          },
        },
        events: [
          {
            event_id: "news-snapshot-added-news-101",
            source_kind: "news",
            entity_kind: "news",
            entity_id: "101",
            detected_at: "2026-07-09T12:00:00.000Z",
            diff_type: "added",
            payload: { title: "Summer Update News" },
          },
        ],
      }),
      "utf8",
    )
    process.env.CTOA_TIBIA_SOURCE_ARCHIVE_DIR = archiveDir

    const sources = await getTibiaSources()
    const updates = await getLatestUpdates()
    const diff = await getDiffLedger("news")

    expect(sources.mode).toBe("local_archive")
    expect(sources.sources[0]).toMatchObject({ status: "fresh", freshness: "live" })
    expect(updates.events).toHaveLength(1)
    expect(diff).toMatchObject({ status: "fresh", events: [{ entity_id: "101", diff_type: "added" }] })
  })

  it("uses safe fallback for unknown OTC builds when no report exists", async () => {
    process.env.CTOA_HELPER_CLIENT_STATE_PATH = path.join(os.tmpdir(), `ctoa-missing-${Date.now()}.json`)
    const clients = await getClients()
    const capabilities = await getClientCapabilities("otc-local-default")

    expect(clients.clients).toHaveLength(1)
    expect(capabilities?.status).toBe("unknown_build")
    expect(capabilities?.protocol_status).toBe("pending_protocol_source")
    expect(capabilities?.safe_fallback).toBe(true)
    expect(capabilities?.heartbeat.status).toBe("missing")
    expect(capabilities?.evidence_status).toBe("stale_snapshot")
    expect(capabilities?.report_error).toBe("missing")
  })

  it("reads a current helper capability heartbeat without inventing protocol readiness", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-client-report-"))
    temporaryRoots.push(root)
    const reportPath = path.join(root, "client.json")
    const observedAt = new Date().toISOString()
    await writeFile(
      reportPath,
      JSON.stringify({
        schema_version: "ctoa-client-capabilities-v1",
        client_id: "otclientv8-local-default",
        client_family: "otclientv8",
        build_id: "1400",
        status: "known_build",
        supported_modules: ["ctoa_native_helper", "ctoa_helper_client_reporter"],
        protocol_status: "pending_protocol_source",
        profile_schema: "ctoa-helper-profile-v1",
        safe_fallback: true,
        observed_at: observedAt,
        observed_at_unix_ms: Date.now(),
        heartbeat_status: "online",
      }),
      "utf8",
    )
    process.env.CTOA_HELPER_CLIENT_STATE_PATH = reportPath

    const clients = await getClients()
    const client = clients.clients[0]
    expect(client.client_id).toBe("otclientv8-local-default")
    expect(client.status).toBe("known_build")
    expect(client.heartbeat.status).toBe("online")
    expect(client.evidence_status).toBe("fresh")
    expect(client.protocol_status).toBe("pending_protocol_source")
    expect(client.safe_fallback).toBe(true)
  })

  it("fails closed for stale and malformed helper reports", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "ctoa-client-report-"))
    temporaryRoots.push(root)
    const reportPath = path.join(root, "client.json")
    const staleAt = Date.now() - 60_000
    await writeFile(
      reportPath,
      JSON.stringify({
        schema_version: "ctoa-client-capabilities-v1",
        client_id: "otclient-local-default",
        client_family: "otclient",
        build_id: "1400",
        status: "known_build",
        supported_modules: [],
        protocol_status: "pending_protocol_source",
        profile_schema: "ctoa-helper-profile-v1",
        safe_fallback: true,
        observed_at: new Date(staleAt).toISOString(),
        observed_at_unix_ms: staleAt,
        heartbeat_status: "online",
      }),
      "utf8",
    )
    process.env.CTOA_HELPER_CLIENT_STATE_PATH = reportPath

    expect((await getClients()).clients[0]).toMatchObject({
      heartbeat: { status: "offline" },
      evidence_status: "stale_snapshot",
      report_error: "stale",
      safe_fallback: true,
    })

    await writeFile(reportPath, "{broken", "utf8")
    expect((await getClients()).clients[0]).toMatchObject({
      status: "unknown_build",
      evidence_status: "parser_broken",
      report_error: "invalid_schema",
      safe_fallback: true,
    })
  })

  it("dry-runs config validation and warns on unknown builds", () => {
    const accepted = validateConfigDryRun({ client_id: "otc-local-default", build_id: "unknown" })
    const rejected = validateConfigDryRun({})

    expect(accepted.ok).toBe(true)
    expect(accepted.warnings).toContain("unknown_build will use safe fallback and pending_protocol_source")
    expect(rejected.ok).toBe(false)
    expect(rejected.errors).toContain("client_id is required")
  })
})
