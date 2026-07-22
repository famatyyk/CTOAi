"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"
import { isControlCenterPublicOps, type ControlCenterPublicOps } from "@/lib/controlCenterPublicOps"

export type { ControlCenterPublicOps } from "@/lib/controlCenterPublicOps"

export const CONTROL_CENTER_PUBLIC_OPS_ENDPOINT = "/api/control-center/ops/public"
export const CONTROL_CENTER_OPS_TIMEOUT_MS = 5000
const CONTROL_CENTER_REFRESH_INTERVAL_MS = 60000

export type ControlCenterDataState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: ControlCenterPublicOps; error: null }
  | { state: "error"; data: null; error: string }

const ControlCenterDataContext = createContext<ControlCenterDataState | null>(null)

const unavailableState: ControlCenterDataState = {
  state: "error",
  data: null,
  error: "Control Center data is unavailable.",
}

/**
 * Browser-only reader for the server-projected public ops contract.  The
 * browser never requests the internal ops payload, which may contain
 * authenticated operational evidence.
 */
export function ControlCenterDataProvider({ children }: { children: ReactNode }) {
  const [dataState, setDataState] = useState<ControlCenterDataState>({ state: "loading", data: null, error: null })

  useEffect(() => {
    let disposed = false
    let loading = false
    const controller = new AbortController()

    async function refresh() {
      if (loading || disposed) return
      loading = true

      try {
        const response = await fetchWithTimeout(
          CONTROL_CENTER_PUBLIC_OPS_ENDPOINT,
          {
            cache: "no-store",
            headers: { Accept: "application/json" },
            signal: controller.signal,
          },
          CONTROL_CENTER_OPS_TIMEOUT_MS,
        )
        if (!response.ok) {
          throw new Error("Control Center public ops response was unavailable.")
        }

        const publicOps = await response.json()
        if (!isControlCenterPublicOps(publicOps)) {
          throw new Error("Control Center public ops response did not match the bounded contract.")
        }
        if (!disposed) {
          setDataState({ state: "ready", data: publicOps, error: null })
        }
      } catch {
        if (!disposed) {
          setDataState({ state: "error", data: null, error: "Control Center data could not be refreshed." })
        }
      } finally {
        loading = false
      }
    }

    void refresh()
    const timer = window.setInterval(() => void refresh(), CONTROL_CENTER_REFRESH_INTERVAL_MS)

    return () => {
      disposed = true
      controller.abort()
      window.clearInterval(timer)
    }
  }, [])

  return <ControlCenterDataContext.Provider value={dataState}>{children}</ControlCenterDataContext.Provider>
}

/**
 * A missing provider fails closed instead of attempting a second browser
 * fetch.  All consumers share one already-bounded public read model.
 */
export function useControlCenterData(): ControlCenterDataState {
  return useContext(ControlCenterDataContext) ?? unavailableState
}
