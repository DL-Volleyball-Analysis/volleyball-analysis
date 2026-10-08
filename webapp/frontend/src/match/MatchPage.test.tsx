import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import type { Rally } from '../api/types'
import { fakeApi } from '../test/fakeApi'
import { rallies, video } from '../test/fixtures'
import { renderApp } from '../test/render'
import { MatchPage } from './MatchPage'

let list: Rally[]
let patchStatus = 200

function setup() {
  const fetch = fakeApi({
    'GET /api/videos/v1': () => ({ body: video({ frames: 750, fps: 25 }) }),
    'GET /api/videos/v1/rallies': () => ({ body: list }),
    'GET /api/videos/v1/stages': () => ({
      body: [{ name: 'court', status: 'unavailable', message: 'court keypoint model not trained yet', summary: {} }],
    }),
    'GET /api/videos/v1/ball': () => ({ body: { fps: 25, frame: [], x: [], y: [] } }),
    'PATCH /api/videos/v1/rallies/0': (init) => {
      const { winner } = JSON.parse(String(init?.body))
      if (patchStatus !== 200) return { status: patchStatus, body: { detail: 'database is locked' } }
      return { body: list.map((r) => (r.idx === 0 ? { ...r, winner_override: winner, effective_winner: winner ?? r.winner } : r)) }
    },
  })
  renderApp(<Routes><Route path="/videos/:id" element={<MatchPage />} /></Routes>, { route: '/videos/v1' })
  return fetch
}

const videoEl = () => document.querySelector('video')!
const rallyRow = (n: number) => within(screen.getByRole('list', { name: 'Rallies' })).getAllByRole('button')[n]
const patches = (fetch: ReturnType<typeof setup>) =>
  fetch.mock.calls.filter(([, init]) => init?.method === 'PATCH').map(([url, init]) => [url, JSON.parse(String(init?.body))])

beforeEach(() => {
  list = rallies(['a', 'b', 'a'], { source: 'demo' })
  patchStatus = 200
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('MatchPage', () => {
  test('labels demo rallies and explains unavailable stages', async () => {
    setup()
    expect(await screen.findByText(/These rallies are placeholders/)).toBeInTheDocument()
    expect(await screen.findByText('court keypoint model not trained yet')).toBeInTheDocument()
  })

  test('selecting a rally seeks to its start', async () => {
    setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.click(rallyRow(2))
    expect(videoEl().currentTime).toBe(20)
  })

  test('J / K move between rallies', async () => {
    setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.keyboard('k')
    expect(videoEl().currentTime).toBe(10)
    await userEvent.keyboard('k')
    expect(videoEl().currentTime).toBe(20)
    await userEvent.keyboard('j')
    expect(videoEl().currentTime).toBe(10)
  })

  test('Space toggles playback', async () => {
    setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.keyboard(' ')
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
  })

  test('1 / 2 / 0 correct the current rally and update the list at once', async () => {
    const fetch = setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.keyboard('2')
    await waitFor(() => expect(within(rallyRow(0)).getByText('B')).toBeInTheDocument())
    await userEvent.keyboard('0')
    await waitFor(() => expect(patches(fetch)).toEqual([
      ['/api/videos/v1/rallies/0', { winner: 'b' }],
      ['/api/videos/v1/rallies/0', { winner: null }],
    ]))
  })

  test('1 / 2 / 0 update the inspector for the current rally', async () => {
    setup()
    await screen.findByText(/These rallies are placeholders/)
    const winner = () => within(screen.getByRole('region', { name: 'Current rally' })).getByText('Winner').closest('div')!
    expect(winner()).toHaveTextContent('A')
    await userEvent.keyboard('2')
    await waitFor(() => expect(winner()).toHaveTextContent('Bedited, model said A'))
    await userEvent.keyboard('0')
    await waitFor(() => expect(winner()).not.toHaveTextContent('edited'))
  })

  test('shortcuts are ignored while a form control has focus', async () => {
    const fetch = setup()
    await screen.findByText(/These rallies are placeholders/)
    screen.getByLabelText('Ball trail').focus()
    await userEvent.keyboard('1')
    expect(patches(fetch)).toEqual([])
  })

  test('a failed correction is rolled back with a notice', async () => {
    patchStatus = 500
    setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.keyboard('2')
    expect(await screen.findByText(/database is locked. The previous winner was restored/)).toBeInTheDocument()
    expect(within(rallyRow(0)).getByText('A')).toBeInTheDocument()
  })
})

describe('MatchPage with rally starts off the 200 ms grid', () => {
  test('J goes back after K landed on a rally start like 2.31 s', async () => {
    list = rallies(['a', 'b', 'a'], { source: 'demo' }).map((r, i) => ({ ...r, start_s: [0.2, 2.31, 4.41][i], end_s: [1.9, 4.0, 6.0][i] }))
    setup()
    await screen.findByText(/These rallies are placeholders/)
    await userEvent.keyboard('k') // t = 0 is before rally 1: K goes to rally 1 (0.2 s)
    expect(videoEl().currentTime).toBe(0.2)
    await userEvent.keyboard('k')
    await userEvent.keyboard('k')
    expect(videoEl().currentTime).toBe(4.41)
    await userEvent.keyboard('j')
    expect(videoEl().currentTime).toBe(2.31)
    await userEvent.keyboard('j')
    expect(videoEl().currentTime).toBe(0.2)
  })
})
