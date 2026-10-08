import { act, Profiler, type ReactNode } from 'react'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import type { Flight, PlayerWindow, Rally } from '../api/types'
import { ClockContext, createClock } from '../playback/clock'
import { fakeApi } from '../test/fakeApi'
import { rallies } from '../test/fixtures'
import { renderApp } from '../test/render'
import { BoardPanel } from './BoardPanel'
import { TacticsBoard2D } from './TacticsBoard2D'
import { ballAt, flightLabel, heightShare } from './flightGeometry'

vi.mock('./TacticsBoard3D', () => ({ default: ({ flights }: { flights: Flight[] }) => <p>3D view with {flights.length} flights</p> }))

/** A straight flight sampled every 0.1 s from (x0, 4.5) to (x1, 4.5), apex 3 m in the middle. */
function flight(patch: Partial<Flight> = {}, x0 = 2, x1 = 14, t0 = 1): Flight {
  const samples = Array.from({ length: 11 }, (_, i) => ({
    t: t0 + i / 10, x: x0 + ((x1 - x0) * i) / 10, y: 4.5, z: 3 - 0.08 * (i - 5) ** 2, observed: i !== 4,
  }))
  return {
    start_s: t0, end_s: t0 + 1, source: 'model', quality: 'ok', reasons: [], fit_px: 1.2, start_speed_mps: 13,
    apex_m: 3, net_crossing: { height_m: 2.9, y_m: 4.5 }, landing: null, samples, ...patch,
  }
}

let frames: FrameRequestCallback[] = []
const step = () => act(() => { const f = frames; frames = []; f.forEach((cb) => cb(0)) })

beforeEach(() => {
  frames = []
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb))
  vi.stubGlobal('cancelAnimationFrame', () => {})
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function withClock(ui: ReactNode) {
  const clock = createClock()
  const video = document.createElement('video')
  clock.attach(video)
  return { clock, video, ...renderApp(<ClockContext.Provider value={clock}>{ui}</ClockContext.Provider>) }
}

describe('flight geometry', () => {
  test('ball position is interpolated within a flight and absent between flights', () => {
    const f = [flight()]
    expect(ballAt(f, 1.05)).toMatchObject({ x: expect.closeTo(2.6, 5) })
    expect(ballAt(f, 0.5)).toBeNull()
    expect(ballAt(f, 2.5)).toBeNull()
  })
  test('height share rises with height and is capped', () => {
    expect(heightShare(0)).toBeLessThan(heightShare(3))
    expect(heightShare(10)).toBe(100)
  })
  test('the label says what matters, including why a flight is low quality', () => {
    expect(flightLabel(flight({ quality: 'low', reasons: ['depth poorly constrained'] }), 0)).toBe(
      'Flight 1, 13 m/s, apex 3.0 m, crosses the net at 2.9 m, low quality: depth poorly constrained')
  })
})

describe('2D tactics board', () => {
  test('ground tracks, labels, landing marks and quality styles', () => {
    withClock(<TacticsBoard2D flights={[
      flight({ landing: { x_m: 15, y_m: 4.5 } }),
      flight({ quality: 'low', reasons: ['fit error 6.0 px'], net_crossing: null, landing: { x_m: 19, y_m: 4 } }, 14, 3, 3),
    ]} />)
    const [first, second] = screen.getAllByTestId('flight')
    expect(first).toHaveAccessibleName(/crosses the net at 2.9 m, lands at x 15.0 m/)
    expect(first.querySelector('[data-observed="false"]')).toHaveAttribute('stroke-dasharray', '1 3') // not seen
    expect(first.querySelector('[data-observed="true"]')).not.toHaveAttribute('stroke-dasharray')
    expect(within(first).getByTestId('landing-in')).toBeInTheDocument()
    expect(within(first).getByTestId('net-height')).toHaveTextContent('2.9 m')
    expect(second).toHaveAccessibleName(/low quality: fit error 6.0 px/)
    second.querySelectorAll('path[data-observed]').forEach((p) => expect(p).toHaveAttribute('stroke-dasharray', '4 3'))
    expect(within(second).getByTestId('landing-out')).toBeInTheDocument()
    expect(first).toHaveAttribute('tabindex', '0') // the reason is reachable by keyboard focus
  })

  test('players at the playback time when they are placed on the court', () => {
    const players: PlayerWindow = { fps: 25, placed: true, boxes: [
      { frame: 25, track_id: 1, x1: 0, y1: 0, x2: 1, y2: 1, interpolated: false, court_x: 4, court_y: 2, side: 'a' },
      { frame: 25, track_id: 2, x1: 0, y1: 0, x2: 1, y2: 1, interpolated: false, court_x: 12, court_y: 6, side: 'b' },
      { frame: 26, track_id: 1, x1: 0, y1: 0, x2: 1, y2: 1, interpolated: false, court_x: 4.1, court_y: 2, side: 'a' },
    ] }
    const { clock } = withClock(<TacticsBoard2D flights={[flight()]} players={players} />)
    act(() => clock.tick(1, true))
    expect(screen.getAllByTestId('player')).toHaveLength(2)
  })

  test('the ball marker follows the video in an animation frame without React commits', () => {
    let commits = 0
    const { video } = withClock(
      <Profiler id="board" onRender={() => { commits++ }}><TacticsBoard2D flights={[flight()]} /></Profiler>,
    )
    const marker = screen.getByTestId('ball-marker')
    step()
    expect(marker).toHaveStyle({ display: 'none' }) // t = 0: before the flight
    const before = commits
    for (const t of [1.2, 1.5, 1.8]) {
      video.currentTime = t
      step()
      expect(Number(marker.getAttribute('cx'))).toBeCloseTo(2 + (12 * (t - 1)), 5)
    }
    expect(marker).not.toHaveStyle({ display: 'none' })
    expect(screen.getByTestId('ball-height').textContent).toMatch(/m$/)
    expect(commits).toBe(before)
  })
})

describe('board panel', () => {
  const rally: Rally = rallies(['a'])[0]

  test('without flights it gives the trajectory stage reason', async () => {
    fakeApi({ 'GET /api/videos/v1/flights': () => ({ body: [] }), 'GET /api/videos/v1/players': () => ({ status: 404 }) })
    withClock(<BoardPanel videoId="v1" rally={rally} trajectory={{ name: 'trajectory', status: 'done', version: '1', summary: {},
      message: 'The camera could not be calibrated because the court was not found, so there are no 3D flights.' }} />)
    expect(await screen.findByText(/could not be calibrated/)).toBeInTheDocument()
  })

  test('demo flights are labelled and the 3D view loads on demand', async () => {
    fakeApi({ 'GET /api/videos/v1/flights': () => ({ body: [flight({ source: 'demo' })] }), 'GET /api/videos/v1/players': () => ({ status: 404 }) })
    withClock(<BoardPanel videoId="v1" rally={rally} />)
    expect(await screen.findByText(/Demo flights/)).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Tactics board with 1 flights' })).toBeInTheDocument()
    expect(screen.queryByText(/3D view with/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '3D' }))
    expect(await screen.findByText('3D view with 1 flights')).toBeInTheDocument()
  })

  test('outside rallies it asks to move into one', () => {
    fakeApi({})
    withClock(<BoardPanel videoId="v1" />)
    expect(screen.getByText(/Move the playhead into a rally/)).toBeInTheDocument()
  })
})
