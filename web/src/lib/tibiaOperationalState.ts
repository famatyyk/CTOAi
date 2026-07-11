import path from "node:path"
import { lstat, open } from "node:fs/promises"

export const TIBIA_OPERATIONAL_STATES = [
  "fresh",
  "source_blocked",
  "parser_broken",
  "unknown_build",
  "pending_protocol_source",
  "stale_snapshot",
] as const

export type TibiaOperationalState = (typeof TIBIA_OPERATIONAL_STATES)[number]

export type RawSnapshot = {
  source_kind: string
  fetched_at: string | null
  url: string
  content_hash: string | null
  blocked_reason?: TibiaOperationalState
}

export type UpdateEvent = {
  event_id: string
  source_kind: string
  entity_kind: string
  entity_id: string
  detected_at: string
  diff_type: "added" | "changed" | "removed" | "blocked" | "parser_error" | "protocol_pending"
  payload: Record<string, unknown>
}

export type SourceInventoryItem = {
  source_kind: string
  label: string
  url: string
  status: Exclude<TibiaOperationalState, "unknown_build" | "pending_protocol_source">
  freshness: "live" | "blocked" | "stale" | "failed"
  raw_snapshot: RawSnapshot
  parser: {
    status: "ready" | "blocked" | "broken" | "pending_fixture"
    normalized_kinds: string[]
    last_error: string | null
  }
  next_action: string
}

export type ClientCapabilities = {
  client_id: string
  client_family: string
  build_id: string
  status: "known_build" | "unknown_build"
  supported_modules: string[]
  protocol_status: "pending_protocol_source" | "ready"
  profile_schema: string
  heartbeat: {
    status: "online" | "offline" | "missing"
    last_seen_at: string | null
  }
  safe_fallback: boolean
  evidence_status: "fresh" | "stale_snapshot" | "parser_broken"
  report_error: "missing" | "invalid_schema" | "stale" | null
  next_action: string
}

export type TelemetryEvent = {
  client_id: string
  event_type: string
  ts: string
  payload: Record<string, unknown>
}

export type ConfigDryRunResult = {
  ok: boolean
  status: "accepted" | "rejected"
  checked_at: string
  errors: string[]
  warnings: string[]
}

const GENERATED_AT = "2026-07-09T00:00:00.000Z"
const CLIENT_REPORT_SCHEMA = "ctoa-client-capabilities-v1"
const CLIENT_REPORT_MAX_BYTES = 64 * 1024
const CLIENT_REPORT_STALE_MS = 15_000
const SOURCE_ARCHIVE_SCHEMA = "ctoa-tibia-source-archive-v1"
const SOURCE_ARCHIVE_INDEX_MAX_BYTES = 1024 * 1024
const ARCHIVE_EVENT_LIMIT = 200

type ClientReport = {
  schema_version: string
  client_id: string
  client_family: string
  build_id: string
  status: "known_build" | "unknown_build"
  supported_modules: string[]
  protocol_status: "pending_protocol_source" | "ready"
  profile_schema: string
  safe_fallback: boolean
  observed_at: string | null
  observed_at_unix_ms: number
  heartbeat_status: "online" | "offline"
}

type TibiaSourcePayload = {
  generated_at: string
  mode: "local_contract" | "local_archive"
  states: readonly TibiaOperationalState[]
  sources: SourceInventoryItem[]
}

type TibiaSourceArchiveIndex = {
  generated_at: string
  sources: Record<string, SourceInventoryItem>
  events: UpdateEvent[]
}

function defaultTibiaSources(): TibiaSourcePayload {
  return {
    generated_at: GENERATED_AT,
    mode: "local_contract",
    states: TIBIA_OPERATIONAL_STATES,
    sources: [
      {
        source_kind: "news",
        label: "Tibia.com News",
        url: "https://www.tibia.com/news/",
        status: "source_blocked",
        freshness: "blocked",
        raw_snapshot: {
          source_kind: "news",
          fetched_at: null,
          url: "https://www.tibia.com/news/",
          content_hash: null,
          blocked_reason: "source_blocked",
        },
        parser: {
          status: "blocked",
          normalized_kinds: ["news/security", "news/fixes", "weapon_proficiency", "boss_difficulty", "monk_virtues"],
          last_error: "Direct live fetch is blocked; keep indexed official URLs and raw snapshot queue visible.",
        },
        next_action: "Capture a raw HTML snapshot through an approved collector, then run fixture parser diff.",
      },
      {
        source_kind: "library",
        label: "Tibia.com Library",
        url: "https://www.tibia.com/library/",
        status: "stale_snapshot",
        freshness: "stale",
        raw_snapshot: {
          source_kind: "library",
          fetched_at: null,
          url: "https://www.tibia.com/library/",
          content_hash: null,
          blocked_reason: "stale_snapshot",
        },
        parser: {
          status: "pending_fixture",
          normalized_kinds: ["creatures", "spells", "achievements", "world_quests", "maps"],
          last_error: null,
        },
        next_action: "Add first raw fixture before marking parser fresh.",
      },
      {
        source_kind: "character_trade",
        label: "Tibia.com Character Trade",
        url: "https://www.tibia.com/charactertrade/",
        status: "stale_snapshot",
        freshness: "stale",
        raw_snapshot: {
          source_kind: "character_trade",
          fetched_at: null,
          url: "https://www.tibia.com/charactertrade/",
          content_hash: null,
          blocked_reason: "stale_snapshot",
        },
        parser: {
          status: "pending_fixture",
          normalized_kinds: ["char_bazaar"],
          last_error: null,
        },
        next_action: "Archive a raw fixture and normalize auction list records.",
      },
      {
        source_kind: "community_test",
        label: "Tibia.com Community/Test",
        url: "https://www.test.tibia.com/forum/",
        status: "source_blocked",
        freshness: "blocked",
        raw_snapshot: {
          source_kind: "community_test",
          fetched_at: null,
          url: "https://www.test.tibia.com/forum/",
          content_hash: null,
          blocked_reason: "source_blocked",
        },
        parser: {
          status: "blocked",
          normalized_kinds: ["weapon_proficiency", "boss_difficulty", "monk_virtues"],
          last_error: "Use raw archived snapshots; do not treat indexed snippets as parser output.",
        },
        next_action: "Queue manual verification for Summer Update 2026 forum surfaces.",
      },
    ],
  }
}

export async function getTibiaSources(): Promise<TibiaSourcePayload> {
  const archive = await readSourceArchiveIndex()
  if (!archive) return { ...defaultTibiaSources(), generated_at: new Date().toISOString() }

  const defaults = defaultTibiaSources()
  return {
    generated_at: archive.generated_at,
    mode: "local_archive",
    states: TIBIA_OPERATIONAL_STATES,
    sources: defaults.sources.map((source) => archive.sources[source.source_kind] ?? source),
  }
}

function defaultLatestUpdates(): { generated_at: string; events: UpdateEvent[] } {
  return {
    generated_at: GENERATED_AT,
    events: [
      {
        event_id: "tibia-news-source-blocked",
        source_kind: "news",
        entity_kind: "source_status",
        entity_id: "news",
        detected_at: GENERATED_AT,
        diff_type: "blocked",
        payload: {
          status: "source_blocked",
          url: "https://www.tibia.com/news/",
          preserve_raw_snapshot: true,
        },
      },
      {
        event_id: "protocol-summer-2026-pending",
        source_kind: "client_adapter",
        entity_kind: "protocol",
        entity_id: "summer-update-2026",
        detected_at: GENERATED_AT,
        diff_type: "protocol_pending",
        payload: {
          status: "pending_protocol_source",
          modules: ["weapon_proficiency", "boss_difficulty", "monk_virtues"],
        },
      },
    ],
  }
}

export async function getLatestUpdates(): Promise<{ generated_at: string; events: UpdateEvent[] }> {
  const archive = await readSourceArchiveIndex()
  if (!archive) {
    const generatedAt = new Date().toISOString()
    const fallback = defaultLatestUpdates()
    return {
      generated_at: generatedAt,
      events: fallback.events.map((event) => ({ ...event, detected_at: generatedAt })),
    }
  }
  return {
    generated_at: archive.generated_at,
    events: archive.events.slice(-ARCHIVE_EVENT_LIMIT),
  }
}

export async function getDiffLedger(surface: string): Promise<{ generated_at: string; surface: string; status: TibiaOperationalState; events: UpdateEvent[] }> {
  const normalizedSurface = surface.trim().toLowerCase() || "unknown"
  const [latest, sources] = await Promise.all([getLatestUpdates(), getTibiaSources()])
  const events = latest.events.filter((event) => event.source_kind === normalizedSurface || event.entity_id === normalizedSurface)
  const source = sources.sources.find((item) => item.source_kind === normalizedSurface)
  return {
    generated_at: latest.generated_at,
    surface: normalizedSurface,
    status: source?.status ?? (events.length > 0 ? "source_blocked" : "stale_snapshot"),
    events,
  }
}

export async function getClients(): Promise<{ generated_at: string; clients: ClientCapabilities[] }> {
  const generatedAt = new Date().toISOString()
  const report = await readClientReport()
  if (report.kind === "valid") {
    const ageMs = Date.now() - report.value.observed_at_unix_ms
    const stale = ageMs > CLIENT_REPORT_STALE_MS
    const safeFallback = report.value.safe_fallback || stale || report.value.status === "unknown_build"
    return {
      generated_at: generatedAt,
      clients: [
        {
          client_id: report.value.client_id,
          client_family: report.value.client_family,
          build_id: report.value.build_id,
          status: report.value.status,
          supported_modules: report.value.supported_modules,
          protocol_status: report.value.protocol_status,
          profile_schema: report.value.profile_schema,
          heartbeat: {
            status: stale ? "offline" : report.value.heartbeat_status,
            last_seen_at: report.value.observed_at,
          },
          safe_fallback: safeFallback,
          evidence_status: stale ? "stale_snapshot" : "fresh",
          report_error: stale ? "stale" : null,
          next_action: stale
            ? "Restart or inspect the sandbox helper; its capability heartbeat is stale."
            : safeFallback
              ? "Keep runtime modules gated until this build and protocol source are verified."
              : "Capability heartbeat is current; continue monitoring version compatibility.",
        },
      ],
    }
  }

  const invalid = report.kind === "invalid"
  return {
    generated_at: generatedAt,
    clients: [
      {
        client_id: "otc-local-default",
        client_family: "otclient",
        build_id: "unknown",
        status: "unknown_build",
        supported_modules: ["helper_ui", "diagnostics", "module_status", "feature_flags", "update_banner"],
        protocol_status: "pending_protocol_source",
        profile_schema: "ctoa-helper-profile-v1",
        heartbeat: {
          status: "missing",
          last_seen_at: null,
        },
        safe_fallback: true,
        evidence_status: invalid ? "parser_broken" : "stale_snapshot",
        report_error: invalid ? "invalid_schema" : "missing",
        next_action: invalid
          ? "Repair or replace the malformed client capability report; runtime remains gated."
          : "Load helper in sandbox and emit heartbeat plus capability report before enabling runtime modules.",
      },
    ],
  }
}

export async function getClientCapabilities(clientId: string): Promise<ClientCapabilities | null> {
  const clients = await getClients()
  return clients.clients.find((client) => client.client_id === clientId) ?? null
}

export async function getTelemetryEvents(): Promise<{ generated_at: string; events: TelemetryEvent[] }> {
  const clients = await getClients()
  const client = clients.clients[0]
  return {
    generated_at: clients.generated_at,
    events: [
      {
        client_id: client.client_id,
        event_type: client.evidence_status === "fresh" ? "capability_heartbeat" : "capability_report_unavailable",
        ts: client.heartbeat.last_seen_at ?? clients.generated_at,
        payload: {
          status: client.status,
          protocol_status: client.protocol_status,
          heartbeat_status: client.heartbeat.status,
          evidence_status: client.evidence_status,
          report_error: client.report_error,
          safe_fallback: client.safe_fallback,
        },
      },
    ],
  }
}

function repoRoot(): string {
  const configured = process.env.CTOA_REPO_ROOT?.trim()
  if (configured) return path.resolve(/*turbopackIgnore: true*/ configured)
  const cwd = process.cwd()
  return path.basename(cwd) === "web"
    ? path.join(/*turbopackIgnore: true*/ process.cwd(), "..")
    : path.join(/*turbopackIgnore: true*/ process.cwd())
}

function clientReportPath(): string {
  const configured = process.env.CTOA_HELPER_CLIENT_STATE_PATH?.trim()
  if (configured) return path.isAbsolute(configured) ? configured : path.join(/*turbopackIgnore: true*/ repoRoot(), configured)
  const localAppData = process.env.LOCALAPPDATA?.trim()
  if (localAppData) {
    return path.join(/*turbopackIgnore: true*/ localAppData, "ctoa_helper_client_ui_preview", "ctoa_client_capabilities.json")
  }
  return path.join(/*turbopackIgnore: true*/ repoRoot(), "runtime", "solteria_helper_dev", "client_capabilities.json")
}

async function readClientReport(): Promise<{ kind: "valid"; value: ClientReport } | { kind: "missing" } | { kind: "invalid" }> {
  const reportPath = clientReportPath()
  let handle: Awaited<ReturnType<typeof open>> | null = null
  try {
    const metadata = await lstat(/* turbopackIgnore: true */ reportPath)
    if (!metadata.isFile() || metadata.isSymbolicLink() || metadata.size > CLIENT_REPORT_MAX_BYTES) return { kind: "invalid" }
    handle = await open(/* turbopackIgnore: true */ reportPath, "r")
    const openedMetadata = await handle.stat()
    if (!openedMetadata.isFile() || openedMetadata.size > CLIENT_REPORT_MAX_BYTES) return { kind: "invalid" }
    const text = await handle.readFile({ encoding: "utf8" })
    const value: unknown = JSON.parse(text)
    return isClientReport(value) ? { kind: "valid", value } : { kind: "invalid" }
  } catch (error) {
    if (isNodeError(error) && error.code === "ENOENT") return { kind: "missing" }
    return { kind: "invalid" }
  } finally {
    await handle?.close()
  }
}

function sourceArchiveIndexPath(): string {
  const configured = process.env.CTOA_TIBIA_SOURCE_ARCHIVE_DIR?.trim()
  const archiveDir = configured
    ? path.isAbsolute(configured)
      ? configured
      : path.join(/*turbopackIgnore: true*/ repoRoot(), configured)
    : path.join(/*turbopackIgnore: true*/ repoRoot(), "runtime", "tibia_source_archive")
  return path.join(/*turbopackIgnore: true*/ archiveDir, "source-index.json")
}

async function readSourceArchiveIndex(): Promise<TibiaSourceArchiveIndex | null> {
  const indexPath = sourceArchiveIndexPath()
  let handle: Awaited<ReturnType<typeof open>> | null = null
  try {
    const metadata = await lstat(/* turbopackIgnore: true */ indexPath)
    if (!metadata.isFile() || metadata.isSymbolicLink() || metadata.size > SOURCE_ARCHIVE_INDEX_MAX_BYTES) return null
    handle = await open(/* turbopackIgnore: true */ indexPath, "r")
    const openedMetadata = await handle.stat()
    if (!openedMetadata.isFile() || openedMetadata.size > SOURCE_ARCHIVE_INDEX_MAX_BYTES) return null
    const text = await handle.readFile({ encoding: "utf8" })
    const value: unknown = JSON.parse(text)
    return isSourceArchiveIndex(value) ? value : null
  } catch {
    return null
  } finally {
    await handle?.close()
  }
}

function isSourceArchiveIndex(value: unknown): value is TibiaSourceArchiveIndex {
  if (!isRecord(value) || value.schema_version !== SOURCE_ARCHIVE_SCHEMA) return false
  if (!isTimestamp(value.generated_at)) return false
  if (!isRecord(value.sources) || !Array.isArray(value.events) || value.events.length > ARCHIVE_EVENT_LIMIT * 3) return false

  const sourceEntries = Object.entries(value.sources)
  return (
    sourceEntries.length <= 16 &&
    sourceEntries.every(([sourceKind, source]) => sourceKind === (isSourceInventoryItem(source) ? source.source_kind : "")) &&
    sourceEntries.every(([, source]) => isSourceInventoryItem(source)) &&
    value.events.every((event) => isUpdateEvent(event))
  )
}

function isSourceInventoryItem(value: unknown): value is SourceInventoryItem {
  if (!isRecord(value) || !isBoundedString(value.source_kind, 64) || !isBoundedString(value.label, 256) || !isBoundedString(value.url, 2048)) return false
  if (!isSourceOperationalState(value.status) || !isSourceFreshness(value.freshness) || !isBoundedString(value.next_action, 1024)) return false
  if (!isRawSnapshot(value.raw_snapshot) || value.raw_snapshot.source_kind !== value.source_kind || !isRecord(value.parser)) return false
  const parser = value.parser
  return (
    (parser.status === "ready" || parser.status === "blocked" || parser.status === "broken" || parser.status === "pending_fixture") &&
    Array.isArray(parser.normalized_kinds) &&
    parser.normalized_kinds.length <= 64 &&
    parser.normalized_kinds.every((kind) => isBoundedString(kind, 128)) &&
    (parser.last_error === null || isBoundedString(parser.last_error, 2048))
  )
}

function isRawSnapshot(value: unknown): value is RawSnapshot {
  if (!isRecord(value) || !isBoundedString(value.source_kind, 64) || !isBoundedString(value.url, 2048)) return false
  if (value.fetched_at !== null && !isTimestamp(value.fetched_at)) return false
  if (value.content_hash !== null && !(typeof value.content_hash === "string" && /^[a-f0-9]{64}$/i.test(value.content_hash))) return false
  return value.blocked_reason === undefined || value.blocked_reason === null || isSourceOperationalState(value.blocked_reason)
}

function isUpdateEvent(value: unknown): value is UpdateEvent {
  if (!isRecord(value) || !isBoundedString(value.event_id, 256) || !isBoundedString(value.source_kind, 64)) return false
  if (!isBoundedString(value.entity_kind, 128) || !isBoundedString(value.entity_id, 256) || !isTimestamp(value.detected_at)) return false
  if (!isRecord(value.payload)) return false
  return (
    value.diff_type === "added" ||
    value.diff_type === "changed" ||
    value.diff_type === "removed" ||
    value.diff_type === "blocked" ||
    value.diff_type === "parser_error" ||
    value.diff_type === "protocol_pending"
  )
}

function isSourceOperationalState(value: unknown): value is SourceInventoryItem["status"] {
  return value === "fresh" || value === "source_blocked" || value === "parser_broken" || value === "stale_snapshot"
}

function isSourceFreshness(value: unknown): value is SourceInventoryItem["freshness"] {
  return value === "live" || value === "blocked" || value === "stale" || value === "failed"
}

function isTimestamp(value: unknown): value is string {
  return isBoundedString(value, 64) && Number.isFinite(Date.parse(value))
}

function isClientReport(value: unknown): value is ClientReport {
  if (!isRecord(value)) return false
  const observedAt = value.observed_at
  const observedAtMs = value.observed_at_unix_ms
  const now = Date.now()
  return (
    value.schema_version === CLIENT_REPORT_SCHEMA &&
    isBoundedString(value.client_id, 128) &&
    isBoundedString(value.client_family, 128) &&
    isBoundedString(value.build_id, 128) &&
    (value.status === "known_build" || value.status === "unknown_build") &&
    Array.isArray(value.supported_modules) &&
    value.supported_modules.length <= 128 &&
    value.supported_modules.every((item) => isBoundedString(item, 128)) &&
    (value.protocol_status === "pending_protocol_source" || value.protocol_status === "ready") &&
    isBoundedString(value.profile_schema, 128) &&
    typeof value.safe_fallback === "boolean" &&
    (observedAt === null || (isBoundedString(observedAt, 64) && Number.isFinite(Date.parse(observedAt)))) &&
    typeof observedAtMs === "number" &&
    Number.isFinite(observedAtMs) &&
    observedAtMs >= 0 &&
    observedAtMs <= now + 60_000 &&
    (value.heartbeat_status === "online" || value.heartbeat_status === "offline")
  )
}

function isBoundedString(value: unknown, maxLength: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maxLength
}

function isNodeError(value: unknown): value is NodeJS.ErrnoException {
  return value instanceof Error && "code" in value
}

export function validateConfigDryRun(input: unknown): ConfigDryRunResult {
  const errors: string[] = []
  const warnings: string[] = []
  const payload = isRecord(input) ? input : {}

  if (!isRecord(input)) {
    errors.push("payload must be a JSON object")
  }

  const clientId = typeof payload.client_id === "string" ? payload.client_id.trim() : ""
  if (!clientId) {
    errors.push("client_id is required")
  }

  const buildId = typeof payload.build_id === "string" ? payload.build_id.trim() : "unknown"
  if (buildId === "unknown") {
    warnings.push("unknown_build will use safe fallback and pending_protocol_source")
  }

  return {
    ok: errors.length === 0,
    status: errors.length === 0 ? "accepted" : "rejected",
    checked_at: GENERATED_AT,
    errors,
    warnings,
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}
