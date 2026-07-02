export type ControlCenterRiskClass = "read_only" | "safe_write" | "guarded_write" | "dangerous" | "forbidden_ui"
export type ControlCenterRole = "owner" | "operator" | "member"

const ROLE_ORDER: Record<ControlCenterRole, number> = {
  member: 1,
  operator: 2,
  owner: 3,
}

export function minimumRoleForRiskClass(riskClass: ControlCenterRiskClass): ControlCenterRole {
  if (riskClass === "read_only") return "member"
  if (riskClass === "safe_write") return "operator"
  return "owner"
}

export function canRunControlCenterAction(
  action: { minimumRole: ControlCenterRole },
  role: ControlCenterRole | null | undefined,
) {
  if (!role) {
    return {
      allowed: false,
      requiredRole: action.minimumRole,
      reason: "Sign in to run Control Center actions.",
    }
  }

  const allowed = ROLE_ORDER[role] >= ROLE_ORDER[action.minimumRole]
  return {
    allowed,
    requiredRole: action.minimumRole,
    reason: allowed ? "" : `${action.minimumRole === "owner" ? "Owner" : "Operator"} role required for this action.`,
  }
}
