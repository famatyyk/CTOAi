export type SameOriginRequestValidation = {
  ok: boolean
  error?: string
}

export function validateSameOriginRequest(
  request: Request,
  options: { requestLabel: string },
): SameOriginRequestValidation {
  const requestOrigin = new URL(request.url).origin
  const origin = request.headers.get("origin")
  const secFetchSite = request.headers.get("sec-fetch-site")?.toLowerCase()
  const crossSiteError = `Cross-site ${options.requestLabel} requests are not allowed.`

  if (origin) {
    try {
      if (new URL(origin).origin !== requestOrigin) {
        return { ok: false, error: crossSiteError }
      }
    } catch {
      return { ok: false, error: `Invalid ${options.requestLabel} request origin.` }
    }
  }

  if (!origin && secFetchSite === "cross-site") {
    return { ok: false, error: crossSiteError }
  }

  const referer = request.headers.get("referer")
  if (!origin && referer) {
    try {
      if (new URL(referer).origin !== requestOrigin) {
        return { ok: false, error: crossSiteError }
      }
    } catch {
      return { ok: false, error: `Invalid ${options.requestLabel} request referer.` }
    }
  }

  return { ok: true }
}
