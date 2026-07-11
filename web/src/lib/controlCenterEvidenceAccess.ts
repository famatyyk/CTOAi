import type { ControlCenterAuthStatus, ControlCenterViewer } from "@/lib/controlCenterAuth"
import { controlCenterRoleMeets, type ControlCenterRole } from "@/lib/controlCenterPolicy"

export type ControlCenterEvidenceAccess =
  | {
      ok: true
      viewer: ControlCenterViewer
    }
  | {
      ok: false
      status: number
      body: {
        ok: false
        error: string
        authStatus: ControlCenterAuthStatus
        requiredRole: ControlCenterRole
      }
    }

export function authorizeControlCenterEvidenceAccess(
  auth: { viewer: ControlCenterViewer | null; authStatus: ControlCenterAuthStatus },
  surfaceLabel = "Control Center evidence",
  requiredRole: ControlCenterRole = "operator",
): ControlCenterEvidenceAccess {
  if (auth.authStatus === "unavailable") {
    return denied(503, `Control Center auth is unavailable; cannot read ${surfaceLabel}.`, auth.authStatus, requiredRole)
  }

  if (!auth.viewer) {
    return denied(
      auth.authStatus === "invalid" ? 403 : 401,
      `Sign in with ${requiredRole} access to read ${surfaceLabel}.`,
      auth.authStatus,
      requiredRole,
    )
  }

  if (!controlCenterRoleMeets(auth.viewer.role, requiredRole)) {
    return denied(403, `${requiredRole === "owner" ? "Owner" : "Operator"} role required to read ${surfaceLabel}.`, auth.authStatus, requiredRole)
  }

  return { ok: true, viewer: auth.viewer }
}

function denied(
  status: number,
  error: string,
  authStatus: ControlCenterAuthStatus,
  requiredRole: ControlCenterRole,
): Extract<ControlCenterEvidenceAccess, { ok: false }> {
  return {
    ok: false,
    status,
    body: {
      ok: false,
      error,
      authStatus,
      requiredRole,
    },
  }
}
