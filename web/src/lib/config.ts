const LOCAL_API_URL = "http://127.0.0.1:8001"

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "")
}

function configuredUrl(value: string | undefined): string {
  return trimTrailingSlash(value?.trim() || LOCAL_API_URL)
}

export function getServerApiUrl(): string {
  return configuredUrl(process.env.VPS_API_URL)
}

export function getPublicApiUrl(): string {
  return configuredUrl(process.env.NEXT_PUBLIC_API_URL)
}
