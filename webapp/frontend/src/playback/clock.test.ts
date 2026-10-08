import { describe, expect, test, vi } from 'vitest'
import { QUANTUM_S, createClock } from './clock'

describe('clock', () => {
  test('60 fps playback notifies subscribers at most 5 times per second', () => {
    const clock = createClock()
    const listener = vi.fn()
    clock.subscribe(listener)
    for (let f = 1; f <= 60; f++) clock.tick(f / 60)
    expect(listener.mock.calls.length).toBeLessThanOrEqual(1 / QUANTUM_S)
    expect(clock.getSnapshot()).toBeCloseTo(1)
  })

  test('a seek is exact, even between quantum steps', () => {
    const clock = createClock()
    clock.tick(2.31, true)
    expect(clock.getSnapshot()).toBe(2.31)
  })

  test('playback after a seek never reads earlier than the seek target', () => {
    const clock = createClock()
    const listener = vi.fn()
    clock.tick(2.31, true)
    clock.subscribe(listener)
    const seen: number[] = []
    for (let f = 1; f <= 60; f++) {
      clock.tick(2.31 + f / 60)
      seen.push(clock.getSnapshot())
    }
    expect(Math.min(...seen)).toBeGreaterThanOrEqual(2.31)
    expect(listener.mock.calls.length).toBeLessThanOrEqual(1 / QUANTUM_S)
  })

  test('seeking backwards is exact', () => {
    const clock = createClock()
    clock.tick(30, true)
    clock.tick(4.5)
    expect(clock.getSnapshot()).toBe(4.5)
  })

  test('unsubscribe stops notifications', () => {
    const clock = createClock()
    const listener = vi.fn()
    const off = clock.subscribe(listener)
    off()
    clock.tick(3, true)
    expect(listener).not.toHaveBeenCalled()
  })

  test('seek moves the attached video and is exact', () => {
    const clock = createClock()
    const video = document.createElement('video')
    clock.attach(video)
    clock.seek(12.53)
    expect(video.currentTime).toBe(12.53)
    expect(clock.getSnapshot()).toBe(12.53)
  })
})
