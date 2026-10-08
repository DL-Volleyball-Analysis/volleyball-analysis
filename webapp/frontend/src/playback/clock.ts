// Playback time outside React state. The overlay canvas reads video.currentTime directly every
// animation frame; React components subscribe to a time that advances in QUANTUM_S steps during
// playback, so playback re-renders them at most 1 / QUANTUM_S = 5 times per second.
import { createContext, useContext, useSyncExternalStore } from 'react'

export const QUANTUM_S = 0.2

export type Clock = ReturnType<typeof createClock>

export function createClock() {
  let video: HTMLVideoElement | null = null
  let time = 0
  let anchor = 0 // last exact time (seek, pause); playback steps are counted from here
  let frame = 0
  const listeners = new Set<() => void>()

  function set(t: number) {
    if (t === time) return
    time = t
    listeners.forEach((l) => l())
  }

  /**
   * Feed a time. During playback (exact = false) the time advances in QUANTUM_S steps from the
   * last exact time, so it never reads earlier than a seek target. Seeks and pauses are exact:
   * after jumping to a rally's start, the app is inside that rally, not just before it.
   */
  function tick(t: number, exact = false) {
    if (exact || t < anchor) {
      anchor = t
      set(t)
      return
    }
    set(anchor + Math.floor((t - anchor) / QUANTUM_S) * QUANTUM_S)
  }

  const sync = () => video && tick(video.currentTime, true)
  function loop() {
    if (video) tick(video.currentTime)
    frame = requestAnimationFrame(loop)
  }
  const onPlay = () => {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(loop)
  }
  const onPause = () => {
    cancelAnimationFrame(frame)
    sync()
  }
  const EVENTS = [['play', onPlay], ['pause', onPause], ['seeked', sync], ['loadedmetadata', sync]] as const

  return {
    tick,
    /** Attach to the page's video element; returns a detach function. */
    attach(el: HTMLVideoElement) {
      video = el
      EVENTS.forEach(([name, fn]) => el.addEventListener(name, fn))
      sync()
      return () => {
        cancelAnimationFrame(frame)
        EVENTS.forEach(([name, fn]) => el.removeEventListener(name, fn))
        if (video === el) video = null
      }
    },
    video: () => video,
    seek(t: number) {
      if (!video) return
      video.currentTime = Math.max(0, t)
      tick(video.currentTime, true)
    },
    pause() {
      video?.pause()
    },
    /** The video's exact current time (the store's time is stepped during playback). */
    exactTime: () => video?.currentTime ?? time,
    togglePlay() {
      if (!video) return
      if (video.paused) void video.play()
      else video.pause()
    },
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    getSnapshot: () => time,
  }
}

export const ClockContext = createContext<Clock | null>(null)

export function useClock(): Clock {
  const clock = useContext(ClockContext)
  if (!clock) throw new Error('useClock needs a ClockContext provider')
  return clock
}

/** Playback time in seconds: exact after a seek or pause, in QUANTUM_S steps while playing. */
export function usePlaybackTime(): number {
  const clock = useClock()
  return useSyncExternalStore(clock.subscribe, clock.getSnapshot)
}
