export type StoredMessage = {
  role: "user" | "assistant"
  content: string
}

export type StoredSession = {
  id: string
  title: string
  createdAt: number
  messages: StoredMessage[]
}

export const MAX_SESSIONS_PER_USER = 20
export const MAX_MESSAGES_PER_SESSION = 80
export const MAX_MESSAGE_CHARS = 4000

const ACTIVE_KEY = "ctoa_active_session"

function sessionsKey(user: string): string {
  return `ctoa_sessions_${user}`
}

function activeKey(user: string): string {
  return `${ACTIVE_KEY}_${user}`
}

function normalizeMessage(message: unknown): StoredMessage | null {
  if (!message || typeof message !== "object") return null
  const role = (message as { role?: unknown }).role
  const content = (message as { content?: unknown }).content
  if ((role !== "user" && role !== "assistant") || typeof content !== "string") return null
  return { role, content: content.slice(0, MAX_MESSAGE_CHARS) }
}

function normalizeSession(session: unknown): StoredSession | null {
  if (!session || typeof session !== "object") return null
  const raw = session as { id?: unknown; title?: unknown; createdAt?: unknown; messages?: unknown }
  if (typeof raw.id !== "string" || typeof raw.title !== "string") return null
  const createdAt = typeof raw.createdAt === "number" && Number.isFinite(raw.createdAt) ? raw.createdAt : Date.now()
  const messages = Array.isArray(raw.messages)
    ? raw.messages.map(normalizeMessage).filter((msg): msg is StoredMessage => Boolean(msg)).slice(-MAX_MESSAGES_PER_SESSION)
    : []
  return {
    id: raw.id,
    title: raw.title.slice(0, 80),
    createdAt,
    messages,
  }
}

export function clampSessions(sessions: StoredSession[]): StoredSession[] {
  return sessions
    .map(normalizeSession)
    .filter((session): session is StoredSession => Boolean(session))
    .sort((a, b) => b.createdAt - a.createdAt)
    .slice(0, MAX_SESSIONS_PER_USER)
}

export function loadUserSessions(user: string, storage: Storage = window.localStorage): StoredSession[] {
  try {
    const raw = storage.getItem(sessionsKey(user))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? clampSessions(parsed) : []
  } catch {
    return []
  }
}

export function saveUserSessions(
  user: string,
  sessions: StoredSession[],
  storage: Storage = window.localStorage,
): StoredSession[] {
  const normalized = clampSessions(sessions)
  try {
    storage.setItem(sessionsKey(user), JSON.stringify(normalized))
    return normalized
  } catch (error) {
    if (!(error instanceof DOMException) || error.name !== "QuotaExceededError") {
      throw error
    }
  }

  const compact = normalized.slice(0, Math.max(1, Math.floor(MAX_SESSIONS_PER_USER / 2))).map((session) => ({
    ...session,
    messages: session.messages.slice(-Math.max(10, Math.floor(MAX_MESSAGES_PER_SESSION / 2))),
  }))
  storage.setItem(sessionsKey(user), JSON.stringify(compact))
  return compact
}

export function loadActiveSessionId(user: string, storage: Storage = window.localStorage): string | null {
  try {
    return storage.getItem(activeKey(user))
  } catch {
    return null
  }
}

export function saveActiveSessionId(user: string, id: string, storage: Storage = window.localStorage): void {
  try {
    storage.setItem(activeKey(user), id)
  } catch {
    // Active id is non-critical; ignore unavailable storage.
  }
}
