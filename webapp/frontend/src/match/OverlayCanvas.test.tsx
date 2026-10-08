import { act } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { ClockContext, createClock } from '../playback/clock'
import { fakeApi } from '../test/fakeApi'
import { renderApp } from '../test/render'
import { OverlayCanvas, type Layers } from './OverlayCanvas'

// jsdom has no canvas or animation frames: record drawing calls and step frames by hand.
const ctx = { setTransform: vi.fn(), clearRect: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), arc: vi.fn() }
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
  fakeApi({ 'GET /api/videos/v1/ball': () => ({ body: { fps: 25, frame: [8, 9, 10], x: [100, 110, 120], y: [50, 52, 54] } }) })
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
  mount({ ball: true, court: false })
  await drawsTrail()
  // ball seen at the current frame (x 120, y 54 in a 1920 x 1080 video) drawn at half scale
  expect(ctx.arc).toHaveBeenCalledWith(60, 27, expect.any(Number), 0, Math.PI * 2)
})

test('turning the layer off stops drawing even with the data loaded', async () => {
  const { setLayers } = mount({ ball: true, court: false })
  await drawsTrail()
  setLayers({ ball: false, court: false })
  ctx.stroke.mockClear()
  ctx.clearRect.mockClear()
  step()
  step()
  expect(ctx.clearRect).toHaveBeenCalled()
  expect(ctx.stroke).not.toHaveBeenCalled()
})

test('draws nothing before the video size is known', async () => {
  mount({ ball: true, court: false }, { w: 0, h: 0 })
  // let the ball data arrive and reach the draw loop before stepping frames
  await act(async () => { await new Promise((r) => setTimeout(r, 50)) })
  for (let i = 0; i < 5; i++) step()
  expect(ctx.clearRect).toHaveBeenCalled()
  expect(ctx.stroke).not.toHaveBeenCalled()
  expect(ctx.arc).not.toHaveBeenCalled()
})
