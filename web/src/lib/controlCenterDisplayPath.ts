import path from "node:path"

function repoRoot(): string {
  const configured = process.env.CTOA_REPO_ROOT?.trim()
  if (configured) return configured
  const cwd = process.cwd()
  return path.resolve(path.basename(cwd) === "web" ? path.dirname(cwd) : cwd)
}

function isWindowsAbsolutePath(value: string): boolean {
  return /^[A-Za-z]:[\\/]/.test(value) || /^\\\\\?\\[A-Za-z]:[\\/]/.test(value)
}

export function toControlCenterDisplayPath(value: string): string {
  const raw = String(value || "")
    .trim()
    .replace(/^\\\\\?\\/, "")
  if (!raw) return ""

  const normalizedRaw = raw.replace(/\\/g, "/")
  const isWindowsPath = isWindowsAbsolutePath(raw)
  if (!path.isAbsolute(raw) && !isWindowsPath) {
    return normalizedRaw.replace(/^\.?\//, "")
  }

  const root = repoRoot()
  if (isWindowsPath) {
    const relative = path.win32.relative(root, raw)
    if (relative && !relative.startsWith("..") && !path.win32.isAbsolute(relative)) {
      return relative.replace(/\\/g, "/")
    }
    return `[external]/${path.win32.basename(raw)}`
  }

  const relative = path.relative(root, raw)
  if (relative && !relative.startsWith("..") && !path.isAbsolute(relative)) {
    return relative.replace(/\\/g, "/")
  }

  return `[external]/${path.basename(raw)}`
}

export function toControlCenterDisplayConfig<T extends Record<string, string>>(config: T): T {
  return Object.fromEntries(Object.entries(config).map(([key, value]) => [key, toControlCenterDisplayPath(value)])) as T
}
