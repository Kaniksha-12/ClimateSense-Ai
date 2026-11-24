export const REQUEST_TIMEOUT_MS = 10000

// Keep pending connections and response bodies bounded, and release resources on navigation.
export async function requestJson(url, { signal, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) controller.abort()
  const timeout = setTimeout(abort, timeoutMs)

  try {
    const response = await fetch(url, { signal: controller.signal })
    if (!response.ok) throw new Error(`Request failed (${response.status})`)
    return await response.json()
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', abort)
  }
}
