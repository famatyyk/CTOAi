import type { ControlCenterRole } from "@/lib/controlCenterPolicy"
import { fetchWithTimeout } from "@/lib/fetchWithTimeout"

export type ControlCenterViewer = {
  username: string
  displayName: string
  role: ControlCenterRole
}

export type ControlCenterAuthStatus = "authenticated" | "unauthenticated" | "invalid" | "unavailable"

export async function resolveControlCenterViewer(
  token: string | undefined,
  apiUrl: string,
  fetchImpl: typeof fetch = (input, init) => fetchWithTimeout(input, init, 4000),
): Promise<{ viewer: ControlCenterViewer | null; authStatus: ControlCenterAuthStatus }> {
  if (!token) {
    return { viewer: null, authStatus: "unauthenticated" }
  }

  try {
    const response = await fetchImpl(`${apiUrl}/api/auth/me`, {
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      return {
        viewer: null,
        authStatus: response.status === 401 || response.status === 403 ? "unauthenticated" : "invalid",
      }
    }

    const data = (await response.json()) as { user?: { username?: string; display_name?: string; role?: ControlCenterRole } }
    const user = data.user
    if (!user?.username || !user?.role) {
      return { viewer: null, authStatus: "invalid" }
    }

    return {
      viewer: {
        username: user.username,
        displayName: user.display_name || user.username,
        role: user.role,
      },
      authStatus: "authenticated",
    }
  } catch {
    return { viewer: null, authStatus: "unavailable" }
  }
}
