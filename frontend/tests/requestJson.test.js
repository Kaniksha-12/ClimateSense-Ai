import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { requestJson } from '../src/services/requestJson.js'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })

function pendingUntilAbort(signal) {
  return new Promise((resolve, reject) => {
    const rejectAbort = () => reject(new DOMException('Aborted', 'AbortError'))
    if (signal.aborted) return rejectAbort()
    signal.addEventListener('abort', rejectAbort, { once: true })
  })
}

test('returns JSON and clears its timeout after success', async () => {
  let requestSignal
  globalThis.fetch = async (url, { signal }) => {
    assert.equal(url, '/api/health')
    requestSignal = signal
    return { ok: true, json: async () => ({ status: 'ok' }) }
  }
  assert.deepEqual(await requestJson('/api/health', { timeoutMs: 5 }), { status: 'ok' })
  await new Promise((resolve) => setTimeout(resolve, 15))
  assert.equal(requestSignal.aborted, false)
})

test('rejects non-success HTTP responses', async () => {
  globalThis.fetch = async () => ({ ok: false, status: 503 })
  await assert.rejects(requestJson('/api/health'), /Request failed \(503\)/)
})

test('propagates malformed JSON errors', async () => {
  globalThis.fetch = async () => ({ ok: true, json: async () => { throw new SyntaxError('Invalid JSON') } })
  await assert.rejects(requestJson('/api/health'), SyntaxError)
})

test('times out a stalled connection', async () => {
  globalThis.fetch = (url, { signal }) => pendingUntilAbort(signal)
  await assert.rejects(requestJson('/api/health', { timeoutMs: 5 }), { name: 'AbortError' })
})

test('timeout covers reading a stalled response body', async () => {
  globalThis.fetch = async (url, { signal }) => ({ ok: true, json: () => pendingUntilAbort(signal) })
  await assert.rejects(requestJson('/api/health', { timeoutMs: 5 }), { name: 'AbortError' })
})

test('forwards caller cancellation', async () => {
  const controller = new AbortController()
  globalThis.fetch = (url, { signal }) => pendingUntilAbort(signal)
  const request = requestJson('/api/health', { signal: controller.signal })
  controller.abort()
  await assert.rejects(request, { name: 'AbortError' })
})

test('honors an already cancelled caller', async () => {
  const controller = new AbortController()
  controller.abort()
  globalThis.fetch = (url, { signal }) => pendingUntilAbort(signal)
  await assert.rejects(requestJson('/api/health', { signal: controller.signal }), { name: 'AbortError' })
})

test('detaches caller cancellation after completion', async () => {
  const controller = new AbortController()
  let requestSignal
  globalThis.fetch = async (url, { signal }) => {
    requestSignal = signal
    return { ok: true, json: async () => ({ status: 'ok' }) }
  }
  await requestJson('/api/health', { signal: controller.signal })
  controller.abort()
  assert.equal(requestSignal.aborted, false)
})

test('propagates network errors without retrying', async () => {
  let attempts = 0
  globalThis.fetch = async () => { attempts += 1; throw new TypeError('Network unavailable') }
  await assert.rejects(requestJson('/api/health'), /Network unavailable/)
  assert.equal(attempts, 1)
})
