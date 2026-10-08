import { vi } from 'vitest'

type Handler = (init?: RequestInit) => { status?: number; body?: unknown }

/** Stub fetch with handlers keyed by "METHOD /api/path" (query string ignored). */
export function fakeApi(routes: Record<string, Handler>) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${url.split('?')[0]}`
    const handler = routes[key]
    if (!handler) return new Response(JSON.stringify({ detail: `no route ${key}` }), { status: 404 })
    const { status = 200, body = null } = handler(init)
    return new Response(status === 204 ? null : JSON.stringify(body), { status })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
