import { act } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { ClockContext, createClock } from '../playback/clock'
import { fakeApi } from '../test/fakeApi'
import { renderApp } from '../test/render'
import { OverlayCanvas, type Layers } from './OverlayCanvas'

// jsdom has no canvas or animation frames: record drawing calls and step frames by hand.
const ctx = { setTransform: vi.fn(), clearRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn(),
  strokeRect: vi.fn(), fillRect: vi.fn(), fillText: vi.fn() }
let frames: FrameRequestCallback[] = []
const step = () => act(() => { const f = frames; frames = []; f.forEach((cb) => cb(0)) })

beforeEach(() => {
  frames = []
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx as never)
  // jsdom has no layout: give the canvas the size of a 960 x 540 player
  vi.spyOn(HTMLCanvasElement.prototype, 'clientWidth', 'get').mockReturnValue(960)
  vi.spyOn(HTMLCanvasElement.prototype, 'clientHeight', 'get').mockReturnValue(540)
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb))
  vi.stubGlobal('cancelAnimationFrame', () => {})
  fakeApi({
    'GET /api/videos/v1/ball': () => ({ body: { fps: 25, frame: [8, 9, 10], x: [100, 110, 120], y: [50, 52, 54] } }),
    'GET /api/videos/v1/players': () => ({ body: { fps: 25, placed: false, boxes: [
      { frame: 10, track_id: 7, x1: 200, y1: 100, x2: 260, y2: 300, interpolated: false, court_x: null, court_y: null, side: null, role: 'player' },
      { frame: 10, track_id: 9, x1: 400, y1: 100, x2: 460, y2: 300, interpolated: false, court_x: null, court_y: null, side: null, role: 'other' },
      { frame: 11, track_id: 8, x1: 0, y1: 0, x2: 10, y2: 10, interpolated: true, court_x: null, court_y: null, side: null, role: 'player' },
    ] } }),
  })
  Object.values(ctx).forEach((f) => typeof f === "function" && f.mockClear())
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function mount(layers: Layers, size = { w: 1920, h: 1080 }) {
  const clock = createClock()
  const video = document.createElement('video')
  Object.defineProperties(video, { videoWidth: { value: size.w }, videoHeight: { value: size.h }, currentTime: { value: 10 / 25, writable: true } })
  clock.attach(video)
  const ui = (l: Layers) => <ClockContext.Provider value={clock}><OverlayCanvas videoId="v1" fps={25} layers={l} /></ClockContext.Provider>
  const r = renderApp(ui(layers))
  return { setLayers: (l: Layers) => r.rerender(ui(l)) }
}

async function drawsTrail() {
  await vi.waitFor(() => {
    step()
    expect(ctx.stroke).toHaveBeenCalled()
  })
}

test('draws the ball trail when the layer is on', async () => {
  mount({ ball: true, court: false, players: false })
  await drawsTrail()
  // ball seen at the current frame (x 120, y 54 in a 1920 x 1080 video) drawn at half scale
  expect(ctx.arc).toHaveBeenCalledWith(60, 27, expect.any(Number), 0, Math.PI * 2)
})

test('turning the layer off stops drawing even with the data loaded', async () => {
  const { setLayers } = mount({ ball: true, court: false, players: false })
  await drawsTrail()
  setLayers({ ball: false, court: false, players: false })
  ctx.stroke.mockClear()
  ctx.clearRect.mockClear()
  step()
  step()
  expect(ctx.clearRect).toHaveBeenCalled()
  expect(ctx.stroke).not.toHaveBeenCalled()
})

test('draws nothing before the video size is known', async () => {
  mount({ ball: true, court: false, players: false }, { w: 0, h: 0 })
  // let the ball data arrive and reach the draw loop before stepping frames
  await act(async () => { await new Promise((r) => setTimeout(r, 50)) })
  for (let i = 0; i < 5; i++) step()
  expect(ctx.clearRect).toHaveBeenCalled()
  expect(ctx.stroke).not.toHaveBeenCalled()
  expect(ctx.arc).not.toHaveBeenCalled()
})


test('player boxes of the current frame are drawn when that layer is on, even without the ball trail', async () => {
  mount({ ball: false, court: false, players: true })
  await vi.waitFor(() => {
    step()
    expect(ctx.strokeRect).toHaveBeenCalled()
  })
  // track 7 at frame 10 (x 200..260, y 100..300 in a 1920 x 1080 video) at half scale; track 8 is another frame
  expect(ctx.strokeRect).toHaveBeenCalledWith(100, 50, 30, 100)
  expect(ctx.fillText).toHaveBeenCalledWith('ID 7', expect.any(Number), expect.any(Number)) // a tracking id, not a shirt number
  expect(ctx.fillText).not.toHaveBeenCalledWith('ID 8', expect.any(Number), expect.any(Number))
  expect(ctx.strokeRect).toHaveBeenCalledWith(200, 50, 30, 100) // the referee is drawn (faint) ...
  expect(ctx.fillText).not.toHaveBeenCalledWith('ID 9', expect.any(Number), expect.any(Number)) // ... but not labelled
  expect(ctx.stroke).not.toHaveBeenCalled() // no ball trail
})


test('a trail segment that jumps across the frame is not drawn', async () => {
  fakeApi({ 'GET /api/videos/v1/ball': () => ({ body: { fps: 25, frame: [8, 9, 10], x: [100, 1500, 120], y: [50, 900, 54] } }) })
  mount({ ball: true, court: false, players: false })
  await vi.waitFor(() => {
    step()
    expect(ctx.arc).toHaveBeenCalled()
  })
  // frames 8 -> 9 -> 10 jump 1400+ px each way in a 1920 px video: no trail segment at all
  expect(ctx.lineTo).not.toHaveBeenCalled()
})
