const LOCAL_API_URL = "http://127.0.0.1:8001"

function isLocalHttpHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase()
  return normalized === "localhost" || normalized === "127.0.0.1" || normalized === "::1" || normalized === "[::1]" || normalized === "host.docker.internal"
}

function configuredUrl(value: string | undefined, envName: string): string {
  const raw = value?.trim() || LOCAL_API_URL
  let parsed: URL

  if (raw.includes("\\")) {
    throw new Error(`${envName} must not include path separators`)
  }

  try {
    parsed = new URL(raw)
  } catch {
    throw new Error(`${envName} must be an absolute HTTP(S) URL`)
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(`${envName} must use http:// or https://`)
  }

  if (parsed.username || parsed.password) {
    throw new Error(`${envName} must not include credentials`)
  }

  if (parsed.protocol === "http:" && !isLocalHttpHost(parsed.hostname)) {
    throw new Error(`${envName} must use https:// for non-local hosts`)
  }

  if (parsed.search || parsed.hash) {
    throw new Error(`${envName} must not include query strings or fragments`)
  }

  if (!/^\/*$/.test(parsed.pathname)) {
    throw new Error(`${envName} must not include path components`)
  }

  return parsed.toString().replace(/\/+$/, "")
}

export function getServerApiUrl(): string {
  return configuredUrl(process.env.VPS_API_URL, "VPS_API_URL")
}

export function getPublicApiUrl(): string {
  return configuredUrl(process.env.NEXT_PUBLIC_API_URL, "NEXT_PUBLIC_API_URL")
}
