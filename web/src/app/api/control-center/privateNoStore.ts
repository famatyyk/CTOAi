/**
 * Operational Control Center responses are user-scoped local evidence. Keep
 * both successful and denied responses out of shared caches.
 */
export const CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS = {
  "Cache-Control": "private, no-store, max-age=0",
  Pragma: "no-cache",
  Vary: "Cookie",
} as const

export function withControlCenterPrivateNoStore(response: Response): Response {
  for (const [name, value] of Object.entries(CONTROL_CENTER_PRIVATE_NO_STORE_HEADERS)) {
    response.headers.set(name, value)
  }
  return response
}
