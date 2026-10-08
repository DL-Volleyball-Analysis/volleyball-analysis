import { afterEach, describe, expect, test, vi } from 'vitest'
import { ApiError, api } from './client'
import { ballWindow, keys } from './queries'

function mockFetch(status: number, body: unknown, statusText = '') {
  const text = typeof body === 'string' ? body : JSON.stringify(body)
  vi.stubGlobal('fetch', vi.fn(async () => new Response(status === 204 ? null : text, { status, statusText })))
}

afterEach(() => vi.unstubAllGlobals())

describe('api errors', () => {
  test('uses FastAPI detail string', async () => {
    mockFetch(409, { detail: 'analysis already queued or running' })
    await expect(api.startJob('v1')).rejects.toEqual(new ApiError(409, 'analysis already queued or running'))
  })

  test('joins validation error messages', async () => {
    mockFetch(422, { detail: [{ msg: 'field required' }, { msg: 'bad stage' }] })
    await expect(api.startJob('v1')).rejects.toThrow('field required; bad stage')
  })

  test('falls back to status text for non-JSON bodies', async () => {
    mockFetch(502, '<html>bad gateway</html>', 'Bad Gateway')
    await expect(api.videos()).rejects.toMatchObject({ status: 502, message: 'Bad Gateway' })
  })

  test('204 resolves without a body', async () => {
    mockFetch(204, null)
    await expect(api.deleteVideo('v1')).resolves.toBeUndefined()
  })

  test('requests go through the /api prefix', async () => {
    mockFetch(200, [])
    await api.rallies('v1')
    expect(fetch).toHaveBeenCalledWith('/api/videos/v1/rallies', undefined)
  })
})

describe('query keys', () => {
  test('per-video data shares the video prefix', () => {
    const prefix = keys.video('v1')
    for (const k of [keys.stages('v1'), keys.rallies('v1'), keys.ball('v1', 2)]) {
      expect(k.slice(0, prefix.length)).toEqual([...prefix])
    }
  })

  test('ball windows are 30 s wide', () => {
    expect([ballWindow(0), ballWindow(29.9), ballWindow(30), ballWindow(-1)]).toEqual([0, 0, 1, 0])
  })
})
