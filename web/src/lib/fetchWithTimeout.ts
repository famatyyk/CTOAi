export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 5000,
): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  const { signal, ...rest } = init
  const onAbort = () => controller.abort()

  if (signal) {
    if (signal.aborted) {
      controller.abort()
    } else {
      signal.addEventListener("abort", onAbort, { once: true })
    }
  }

  try {
    return await fetch(input, {
      ...rest,
      signal: controller.signal,
    })
  } finally {
    signal?.removeEventListener("abort", onAbort)
    clearTimeout(timeout)
  }
}
