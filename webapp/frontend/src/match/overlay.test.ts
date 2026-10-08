import { describe, expect, test } from 'vitest'
import { letterbox, trailPoints } from './overlay'

describe('letterbox', () => {
  test('wide box: bars left and right', () => {
    expect(letterbox(1920, 1080, 1000, 400)).toEqual({ scale: 400 / 1080, x: (1000 - 1920 * (400 / 1080)) / 2, y: 0 })
  })
  test('tall box: bars top and bottom', () => {
    const lb = letterbox(1920, 1080, 960, 1000)
    expect(lb.scale).toBe(0.5)
    expect(lb.x).toBe(0)
    expect(lb.y).toBe((1000 - 540) / 2)
  })
  test('video size not known yet', () => {
    expect(letterbox(0, 0, 800, 450)).toEqual({ scale: 0, x: 0, y: 0 })
  })
})

describe('trailPoints', () => {
  const w0 = { fps: 25, frame: [8, 9, 10, 11], x: [1, null, 3, 4], y: [1, null, 3, 4] }
  const w1 = { fps: 25, frame: [12, 13], x: [5, 6], y: [5, 6] }

  test('takes the last `length` frames across windows, oldest first, skipping misses', () => {
    expect(trailPoints([w1, w0], 12, 4).map((p) => p.frame)).toEqual([10, 11, 12])
  })
  test('nothing after the current frame', () => {
    expect(trailPoints([w0, w1], 10, 3).map((p) => p.frame)).toEqual([8, 10])
  })
})
