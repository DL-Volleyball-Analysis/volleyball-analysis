// Pure helpers for drawing on top of the video (unit tested; the canvas code stays thin).
import type { BallWindow } from '../api/types'

export type Letterbox = { scale: number; x: number; y: number }

/** Where a videoW x videoH frame sits inside a boxW x boxH element with object-fit: contain. */
export function letterbox(videoW: number, videoH: number, boxW: number, boxH: number): Letterbox {
  if (!videoW || !videoH) return { scale: 0, x: 0, y: 0 }
  const scale = Math.min(boxW / videoW, boxH / videoH)
  return { scale, x: (boxW - videoW * scale) / 2, y: (boxH - videoH * scale) / 2 }
}

export type Point = { x: number; y: number; frame: number }

/**
 * Detected ball positions in (frame - length, frame], oldest first, in video pixels.
 * Windows may arrive in any order and overlap; missing frames are skipped (never invented).
 */
export function trailPoints(windows: readonly BallWindow[], frame: number, length: number): Point[] {
  const out: Point[] = []
  for (const w of windows) {
    for (let i = 0; i < w.frame.length; i++) {
      const f = w.frame[i]
      const x = w.x[i]
      const y = w.y[i]
      if (f > frame - length && f <= frame && x != null && y != null) out.push({ x, y, frame: f })
    }
  }
  return out.sort((a, b) => a.frame - b.frame)
}
