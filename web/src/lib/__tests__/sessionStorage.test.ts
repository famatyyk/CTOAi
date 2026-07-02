import { describe, expect, it } from "vitest"
import { MAX_MESSAGE_CHARS, MAX_MESSAGES_PER_SESSION, MAX_SESSIONS_PER_USER, loadUserSessions, saveUserSessions } from "../sessionStorage"

class MemoryStorage implements Storage {
  private store = new Map<string, string>()
  length = 0
  clear(): void { this.store.clear(); this.length = 0 }
  getItem(key: string): string | null { return this.store.get(key) ?? null }
  key(index: number): string | null { return Array.from(this.store.keys())[index] ?? null }
  removeItem(key: string): void { this.store.delete(key); this.length = this.store.size }
  setItem(key: string, value: string): void { this.store.set(key, value); this.length = this.store.size }
}

class QuotaStorage extends MemoryStorage {
  failed = false
  setItem(key: string, value: string): void {
    if (!this.failed) {
      this.failed = true
      throw new DOMException("quota", "QuotaExceededError")
    }
    super.setItem(key, value)
  }
}

describe("sessionStorage helpers", () => {
  it("returns empty sessions for invalid JSON", () => {
    const storage = new MemoryStorage()
    storage.setItem("ctoa_sessions_alice", "not-json")

    expect(loadUserSessions("alice", storage)).toEqual([])
  })

  it("normalizes session and message limits", () => {
    const storage = new MemoryStorage()
    const sessions = Array.from({ length: MAX_SESSIONS_PER_USER + 5 }, (_, index) => ({
      id: String(index),
      title: "t".repeat(120),
      createdAt: index,
      messages: Array.from({ length: MAX_MESSAGES_PER_SESSION + 5 }, () => ({
        role: "user" as const,
        content: "x".repeat(MAX_MESSAGE_CHARS + 10),
      })),
    }))

    const saved = saveUserSessions("alice", sessions, storage)

    expect(saved).toHaveLength(MAX_SESSIONS_PER_USER)
    expect(saved[0].id).toBe(String(MAX_SESSIONS_PER_USER + 4))
    expect(saved[0].title).toHaveLength(80)
    expect(saved[0].messages).toHaveLength(MAX_MESSAGES_PER_SESSION)
    expect(saved[0].messages[0].content).toHaveLength(MAX_MESSAGE_CHARS)
  })

  it("compacts sessions after quota errors", () => {
    const storage = new QuotaStorage()
    const saved = saveUserSessions("alice", [
      { id: "1", title: "one", createdAt: 1, messages: [{ role: "user", content: "hello" }] },
      { id: "2", title: "two", createdAt: 2, messages: [{ role: "assistant", content: "czesc" }] },
    ], storage)

    expect(saved.length).toBeGreaterThan(0)
    expect(loadUserSessions("alice", storage).length).toBeGreaterThan(0)
  })
})
