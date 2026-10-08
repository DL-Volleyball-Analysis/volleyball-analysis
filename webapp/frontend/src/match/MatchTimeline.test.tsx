import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { ClockContext, createClock } from '../playback/clock'
import { fakeApi } from '../test/fakeApi'
import { rallies } from '../test/fixtures'
import { renderApp } from '../test/render'
import { MatchTimeline } from './MatchTimeline'
import { rulerStep, timeAt } from './timeline'

describe('timeline helpers', () => {
  test('ruler step keeps labels to about ten', () => {
    expect([rulerStep(8), rulerStep(60), rulerStep(3600)]).toEqual([1, 10, 600])
    expect(rulerStep(8, 4)).toBe(5) // a narrow track fits fewer labels: 0 and 5 s
  })
  test('time at a position is clamped to the video', () => {
    const box = { left: 100, width: 400 }
    expect([timeAt(300, box, 60), timeAt(50, box, 60), timeAt(900, box, 60)]).toEqual([30, 0, 60])
  })
})

let frames: FrameRequestCallback[] = []
const step = () => act(() => { const f = frames; frames = []; f.forEach((cb) => cb(0)) })

beforeEach(() => {
  frames = []
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb))
  vi.stubGlobal('cancelAnimationFrame', () => {})
  fakeApi({ 'GET /api/videos/v1/ball/coverage': () => ({ body: { duration_s: 30, coverage: [1, 0.5, 0, 1] } }) })
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function mount(onSelect = vi.fn()) {
  const list = rallies(['a', 'b', null])
  list[0] = { ...list[0], landing_x: 4, landing_y: 4 }
  list[1] = { ...list[1], landing_x: 19, landing_y: 4, confidence: 0.3 }
  list[2] = { ...list[2], landing_x: null, landing_y: null }
  const clock = createClock()
  const video = document.createElement('video')
  clock.attach(video)
  renderApp(
    <ClockContext.Provider value={clock}>
      <MatchTimeline videoId="v1" rallies={list} duration={30} currentIndex={1} onSelect={onSelect} />
    </ClockContext.Provider>,
  )
  return { list, video, onSelect }
}

describe('MatchTimeline', () => {
  test('lanes show rallies, ball coverage, landings and review marks', async () => {
    mount()
    expect(screen.getByRole('button', { name: /Rally 2, won by B, .*needs review/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByRole('button', { name: /Rally 3, winner unknown/ })).toBeInTheDocument()
    expect(await screen.findAllByTestId('landing-in')).toHaveLength(1)
    expect(screen.getAllByTestId('landing-out')).toHaveLength(1)
    expect(screen.getAllByTestId('review-mark')).toHaveLength(1)
    await vi.waitFor(() => expect(screen.getByTestId('lane-ball').querySelectorAll('rect')).toHaveLength(4))
  })

  test('selecting a rally block or a review mark hands over the rally', async () => {
    const { list, onSelect } = mount()
    await userEvent.click(screen.getByRole('button', { name: /Rally 1/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Review rally 2' }))
    expect(onSelect.mock.calls.map(([r]) => r.idx)).toEqual([list[0].idx, list[1].idx])
  })

  test('click and drag on the track seek the video', () => {
    const { video } = mount()
    const track = screen.getByTestId('timeline-track')
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 300 } as DOMRect)
    fireEvent.pointerDown(track, { clientX: 150, pointerId: 1 })
    expect(video.currentTime).toBe(15)
    fireEvent.pointerMove(track, { clientX: 240, pointerId: 1 })
    expect(video.currentTime).toBe(24)
    fireEvent.pointerUp(track, { pointerId: 1 })
    fireEvent.pointerMove(track, { clientX: 30, pointerId: 1 })
    expect(video.currentTime).toBe(24) // no drag after release
  })

  test('the playhead follows the video every frame', () => {
    const { video } = mount()
    video.currentTime = 7.5
    step()
    expect(screen.getByTestId('playhead').style.left).toBe('25%')
  })
})

describe('MatchTimeline rendering cost', () => {
  test('moving the playhead does not re-render React', async () => {
    const { Profiler } = await import('react')
    const commits = vi.fn()
    const clock = createClock()
    const video = document.createElement('video')
    clock.attach(video)
    renderApp(
      <ClockContext.Provider value={clock}>
        <Profiler id="t" onRender={commits}>
          <MatchTimeline videoId="v1" rallies={rallies(['a'])} duration={30} currentIndex={0} onSelect={() => {}} />
        </Profiler>
      </ClockContext.Provider>,
    )
    await vi.waitFor(() => expect(screen.getByTestId('lane-ball').querySelectorAll('rect')).toHaveLength(4))
    const before = commits.mock.calls.length
    for (let i = 1; i <= 60; i++) {
      video.currentTime = i / 2
      step()
    }
    expect(commits.mock.calls.length).toBe(before)
    expect(screen.getByTestId('playhead').style.left).toBe('100%')
  })
})
