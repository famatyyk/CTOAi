import { lstat, open } from "node:fs/promises"

/**
 * The Control Center only consumes small, local evidence artifacts.  Keeping
 * the limit here makes the boundary reusable by every capability collector.
 */
export const CONTROL_CENTER_EVIDENCE_JSON_MAX_BYTES = 512 * 1024
export const CONTROL_CENTER_ACTION_AUDIT_MAX_BYTES = 1024 * 1024

export type BoundedControlCenterAuditLines = {
  lines: string[]
  truncated: boolean
  sourceBytes: number
  sampledBytes: number
}

type SafeFileHandle = Awaited<ReturnType<typeof open>>

/**
 * Read a regular, non-symlink file only when it remains stable during the
 * read.  Returning null is intentional: evidence is advisory and an unsafe
 * or racing artifact must never be treated as a valid one.
 */
export async function readBoundedControlCenterText(
  filePath: string,
  maxBytes = CONTROL_CENTER_EVIDENCE_JSON_MAX_BYTES,
): Promise<string | null> {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) return null

  let handle: SafeFileHandle | null = null
  try {
    const pathInfo = await lstat(filePath)
    if (pathInfo.isSymbolicLink() || !pathInfo.isFile() || pathInfo.size > maxBytes) {
      return null
    }

    handle = await open(filePath, "r")
    const fileInfo = await handle.stat()
    // Do not follow a path that was swapped between lstat() and open().
    if (
      !fileInfo.isFile() ||
      fileInfo.size !== pathInfo.size ||
      fileInfo.mtimeMs !== pathInfo.mtimeMs ||
      fileInfo.size > maxBytes
    ) {
      return null
    }

    const sourceBytes = fileInfo.size
    const buffer = Buffer.alloc(sourceBytes)
    const sampledBytes = await readFully(handle, buffer, 0)
    if (sampledBytes !== sourceBytes) return null

    const fileStat = await lstat(filePath)
    if (
      fileStat.isSymbolicLink() ||
      !fileStat.isFile() ||
      fileStat.size !== sourceBytes ||
      fileStat.mtimeMs !== fileInfo.mtimeMs
    ) {
      return null
    }

    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(buffer)
    } catch {
      return null
    }
  } catch {
    return null
  } finally {
    await handle?.close().catch(() => undefined)
  }
}

/**
 * Strict JSON keeps duplicate object keys from silently replacing prior
 * values.  Only object payloads are accepted at this boundary.
 */
export async function readStrictControlCenterJson(filePath: string): Promise<Record<string, unknown> | null> {
  const text = await readBoundedControlCenterText(filePath)
  if (text === null || jsonHasDuplicateObjectKeys(text)) return null

  try {
    const parsed: unknown = JSON.parse(text)
    return isRecord(parsed) ? parsed : null
  } catch {
    return null
  }
}

// Explicit alias for dependency injection and tests; both readers retain the
// same strict, fail-closed contract.
export const readControlCenterJson = readStrictControlCenterJson

/**
 * Return a stable suffix of an append-only JSONL audit.  The first partial
 * line is discarded, so the caller never parses a record cut in half.
 */
export async function readBoundedControlCenterActionAuditLines(
  filePath: string,
  maxBytes = CONTROL_CENTER_ACTION_AUDIT_MAX_BYTES,
): Promise<BoundedControlCenterAuditLines> {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) {
    throw new Error("Control Center action audit limit is invalid.")
  }

  let handle: SafeFileHandle | null = null
  try {
    const pathInfo = await lstat(filePath)
    if (pathInfo.isSymbolicLink() || !pathInfo.isFile()) {
      throw new Error("Control Center action audit path is not safe to read.")
    }

    const sourceBytes = pathInfo.size
    if (sourceBytes <= 0) {
      return { lines: [], truncated: false, sourceBytes: 0, sampledBytes: 0 }
    }

    handle = await open(filePath, "r")
    const fileInfo = await handle.stat()
    if (
      !fileInfo.isFile() ||
      fileInfo.size !== pathInfo.size ||
      fileInfo.mtimeMs !== pathInfo.mtimeMs
    ) {
      throw new Error("Control Center action audit changed while opening.")
    }

    const requestedBytes = Math.min(sourceBytes, maxBytes)
    const start = Math.max(0, sourceBytes - requestedBytes)
    const buffer = Buffer.alloc(requestedBytes)
    const sampledBytes = await readFully(handle, buffer, start)
    if (sampledBytes !== requestedBytes) {
      throw new Error("Control Center action audit changed while reading.")
    }

    const fileStat = await lstat(filePath)
    if (
      fileStat.isSymbolicLink() ||
      !fileStat.isFile() ||
      fileStat.size !== sourceBytes ||
      fileStat.mtimeMs !== fileInfo.mtimeMs
    ) {
      throw new Error("Control Center action audit changed while reading.")
    }

    let text: string
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(buffer)
    } catch {
      throw new Error("Control Center action audit is not UTF-8.")
    }

    const truncated = start > 0
    if (truncated) {
      const firstNewline = text.indexOf("\n")
      text = firstNewline >= 0 ? text.slice(firstNewline + 1) : ""
    }

    return {
      lines: text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean),
      truncated,
      sourceBytes,
      sampledBytes,
    }
  } finally {
    await handle?.close().catch(() => undefined)
  }
}

async function readFully(handle: SafeFileHandle, buffer: Buffer, position: number): Promise<number> {
  let offset = 0
  while (offset < buffer.length) {
    const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset, position + offset)
    if (bytesRead <= 0) break
    offset += bytesRead
  }
  return offset
}

/**
 * JSON.parse accepts duplicate object keys.  Evidence does not: duplicate
 * keys make the claimed artifact ambiguous, including inside nested objects.
 */
export function jsonHasDuplicateObjectKeys(text: string): boolean {
  let index = 0
  let duplicate = false
  const whitespace = /\s/

  const skipWhitespace = () => {
    while (index < text.length && whitespace.test(text[index])) index += 1
  }
  const parseStringToken = (): string => {
    const start = index
    if (text[index] !== '"') throw new Error("expected JSON string")
    index += 1
    while (index < text.length) {
      const character = text[index]
      if (character === "\\") {
        index += 2
        continue
      }
      index += 1
      if (character === '"') return JSON.parse(text.slice(start, index)) as string
    }
    throw new Error("unterminated JSON string")
  }
  const parseValue = (): void => {
    skipWhitespace()
    const character = text[index]
    if (character === "{") {
      parseObject()
      return
    }
    if (character === "[") {
      index += 1
      skipWhitespace()
      if (text[index] === "]") {
        index += 1
        return
      }
      while (index < text.length) {
        parseValue()
        skipWhitespace()
        if (text[index] === "]") {
          index += 1
          return
        }
        if (text[index] !== ",") throw new Error("invalid JSON array")
        index += 1
      }
      throw new Error("unterminated JSON array")
    }
    if (character === '"') {
      parseStringToken()
      return
    }
    const start = index
    while (index < text.length && !/[\s,}\]]/.test(text[index])) index += 1
    if (start === index) throw new Error("invalid JSON value")
  }
  const parseObject = (): void => {
    index += 1
    const keys = new Set<string>()
    skipWhitespace()
    if (text[index] === "}") {
      index += 1
      return
    }
    while (index < text.length) {
      skipWhitespace()
      const key = parseStringToken()
      if (keys.has(key)) duplicate = true
      keys.add(key)
      skipWhitespace()
      if (text[index] !== ":") throw new Error("invalid JSON object")
      index += 1
      parseValue()
      skipWhitespace()
      if (text[index] === "}") {
        index += 1
        return
      }
      if (text[index] !== ",") throw new Error("invalid JSON object")
      index += 1
    }
    throw new Error("unterminated JSON object")
  }

  try {
    skipWhitespace()
    parseValue()
    skipWhitespace()
    return duplicate || index !== text.length
  } catch {
    return true
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}
