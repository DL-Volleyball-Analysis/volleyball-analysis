import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import type { Tag } from '../api/types'
import { MatchPage } from '../match/MatchPage'
import { fakeApi } from '../test/fakeApi'
import { rallies, video } from '../test/fixtures'
import { renderApp } from '../test/render'

let tags: Tag[]

const tagOut = (patch: Partial<Tag> = {}): Tag => ({
  id: 't1', time_s: 4, kind: 'attack', team: 'a', number: 10, outcome: null, effective_outcome: 'kill',
  inferred: true, rally_idx: 0, ...patch,
})

function setup() {
  const fetch = fakeApi({
    'GET /api/videos/v1': () => ({ body: video({ frames: 750, fps: 25 }) }),
    'GET /api/videos/v1/rallies': () => ({ body: rallies(['a', 'b', 'a']) }),
    'GET /api/videos/v1/stages': () => ({ body: [] }),
    'GET /api/videos/v1/ball': () => ({ body: { fps: 25, frame: [], x: [], y: [] } }),
    'GET /api/videos/v1/tags': () => ({ body: tags }),
    'POST /api/videos/v1/tags': (init) => {
      const body = JSON.parse(String(init?.body))
      tags = [...tags, tagOut({ id: 'new', ...body })]
      return { status: 201, body: tags }
    },
    'PATCH /api/videos/v1/tags/t1': (init) => {
      const { outcome } = JSON.parse(String(init?.body))
      tags = tags.map((t) => (t.id === 't1' ? { ...t, outcome, effective_outcome: outcome ?? 'kill', inferred: outcome == null } : t))
      return { body: tags }
    },
    'DELETE /api/videos/v1/tags/t1': () => {
      tags = tags.filter((t) => t.id !== 't1')
      return { body: tags }
    },
  })
  renderApp(<Routes><Route path="/videos/:id" element={<MatchPage />} /></Routes>, { route: '/videos/v1' })
  return fetch
}

const calls = (fetch: ReturnType<typeof setup>, method: string) =>
  fetch.mock.calls.filter(([, init]) => init?.method === method).map(([url, init]) => [url, init?.body ? JSON.parse(String(init.body)) : null])

beforeEach(() => {
  tags = []
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('tagging on the match page', () => {
  test('T pauses, opens the entry at the playhead, and number + Enter saves an attack', async () => {
    const fetch = setup()
    await screen.findAllByRole('button', { name: /^Rally 1/ })
    document.querySelector('video')!.currentTime = 4.2
    await userEvent.keyboard('t')
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    const entry = screen.getByRole('region', { name: 'New tag' })
    expect(within(entry).getByText('at 0:04.2')).toBeInTheDocument()
    await userEvent.keyboard('10{Enter}')
    await waitFor(() => expect(screen.queryByRole('region', { name: 'New tag' })).not.toBeInTheDocument())
    expect(calls(fetch, 'POST')).toEqual([['/api/videos/v1/tags', { time_s: 4.2, kind: 'attack', team: 'a', number: 10 }]])
    expect(await screen.findByRole('button', { name: 'Attack by A 10, kill (from the winner)' })).toBeInTheDocument()
  })

  test('S tags a serve and the next entry keeps the last team', async () => {
    const fetch = setup()
    await screen.findAllByRole('button', { name: /^Rally 1/ })
    await userEvent.keyboard('s')
    await userEvent.keyboard('b3{Enter}')
    await waitFor(() => expect(calls(fetch, 'POST')).toHaveLength(1))
    expect(calls(fetch, 'POST')[0][1]).toMatchObject({ kind: 'serve', team: 'b', number: 3 })
    await waitFor(() => expect(screen.queryByRole('region', { name: 'New tag' })).not.toBeInTheDocument())
    await userEvent.keyboard('t')
    const entry = screen.getByRole('region', { name: 'New tag' })
    expect(within(entry).getByRole('button', { name: 'B' })).toHaveAttribute('aria-pressed', 'true')
  })

  test('typing a number does not trigger the rally shortcuts', async () => {
    const fetch = setup()
    await screen.findAllByRole('button', { name: /^Rally 1/ })
    await userEvent.keyboard('t')
    await userEvent.keyboard('12')
    expect(calls(fetch, 'PATCH')).toEqual([]) // 1 / 2 would have corrected the rally winner
  })

  test('a tag on the timeline opens in the inspector to set the outcome or delete it', async () => {
    tags = [tagOut()]
    const fetch = setup()
    await userEvent.click(await screen.findByRole('button', { name: 'Attack by A 10, kill (from the winner)' }))
    expect(document.querySelector('video')!.currentTime).toBe(4)
    const inspector = screen.getByRole('region', { name: 'Selected tag' })
    await userEvent.selectOptions(within(inspector).getByRole('combobox', { name: 'Outcome' }), 'in_play')
    await waitFor(() => expect(calls(fetch, 'PATCH')).toEqual([['/api/videos/v1/tags/t1', { outcome: 'in_play' }]]))
    await userEvent.click(within(inspector).getByRole('button', { name: 'Delete tag' }))
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Selected tag' })).not.toBeInTheDocument())
    expect(screen.queryAllByTestId('tag-mark')).toHaveLength(0)
  })
})
