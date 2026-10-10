import { useEffect, useRef } from 'react'
import { BALL_WINDOW_S, ballWindow, useBallWindow, usePlayers } from '../api/queries'
import type { BallWindow, PlayerWindow } from '../api/types'
import { useClock, usePlaybackTime } from '../playback/clock'
import { boxesAt, letterbox, trailPoints } from './overlay'

export type Layers = { ball: boolean; court: boolean; players: boolean }

const TRAIL_S = 0.5
const JUMP = 0.08 // same threshold as the ball-tracking jump proxy (vball.metrics)
// Overlay colours sit on video, not on the page theme: bright core, dark edge for any background.
const BALL = '#ffd23f'
const EDGE = 'rgba(0, 0, 0, 0.75)'
const PLAYER = '#ffffff'

/** Draws on top of the video every animation frame, reading video.currentTime directly. */
export function OverlayCanvas({ videoId, fps, layers }: { videoId: string; fps: number; layers: Layers }) {
  const clock = useClock()
  const canvas = useRef<HTMLCanvasElement>(null)

  // Ball data for the windows around the playhead (time quantised to 200 ms, so this
  // component re-renders at most 5 times per second; drawing does not depend on it).
  const w = ballWindow(usePlaybackTime())
  const current = useBallWindow(videoId, w, layers.ball)
  const previous = useBallWindow(videoId, w - 1, layers.ball && w > 0)
  useBallWindow(videoId, w + 1, layers.ball) // prefetch
  const players = usePlayers(videoId, w * BALL_WINDOW_S, (w + 1) * BALL_WINDOW_S, layers.players)
  // The draw loop below reads these refs; update them after each commit, not during render.
  const windows = useRef<BallWindow[]>([])
  const playerWindows = useRef<PlayerWindow[]>([])
  const layersRef = useRef(layers)
  useEffect(() => {
    windows.current = [previous.data, current.data].filter((d): d is BallWindow => d !== undefined)
    playerWindows.current = players.data ? [players.data] : []
    layersRef.current = layers
  })

  useEffect(() => {
    const el = canvas.current
    const ctx = el?.getContext('2d')
    if (!el || !ctx) return
    let frame = 0

    const draw = () => {
      frame = requestAnimationFrame(draw)
      const video = clock.video()
      const dpr = window.devicePixelRatio || 1
      const { clientWidth: w, clientHeight: h } = el
      if (el.width !== Math.round(w * dpr) || el.height !== Math.round(h * dpr)) {
        el.width = Math.round(w * dpr)
        el.height = Math.round(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)
      if (!video || !(layersRef.current.ball || layersRef.current.players)) return

      const lb = letterbox(video.videoWidth, video.videoHeight, w, h)
      if (!lb.scale) return // video size not known yet: every point would land in the corner

      const now = Math.round(video.currentTime * fps)
      if (layersRef.current.players) {
        ctx.font = '600 11px ui-monospace, monospace'
        for (const b of boxesAt(playerWindows.current, now)) {
          const x = lb.x + b.x1 * lb.scale
          const y = lb.y + b.y1 * lb.scale
          const bw = (b.x2 - b.x1) * lb.scale
          const bh = (b.y2 - b.y1) * lb.scale
          const other = b.role === 'other' // officials, staff, spectators: shown faint, not labelled
          ctx.globalAlpha = other ? 0.35 : 1
          ctx.strokeStyle = EDGE
          ctx.lineWidth = 3
          ctx.strokeRect(x, y, bw, bh)
          ctx.strokeStyle = PLAYER
          ctx.lineWidth = 1.5
          ctx.strokeRect(x, y, bw, bh)
          ctx.globalAlpha = 1
          if (other) continue
          const label = `ID ${b.track_id}` // a tracking id, not the shirt number
          ctx.fillStyle = EDGE
          ctx.fillRect(x, y - 14, 8 + 7 * label.length, 14)
          ctx.fillStyle = PLAYER
          ctx.fillText(label, x + 4, y - 3)
        }
      }
      if (!layersRef.current.ball) return
      const pts = trailPoints(windows.current, now, Math.round(TRAIL_S * fps))
      const px = (p: { x: number; y: number }) => [lb.x + p.x * lb.scale, lb.y + p.y * lb.scale] as const

      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      for (let i = 1; i < pts.length; i++) {
        // fade older segments; skip across gaps longer than 3 frames (missed detections)
        if (pts[i].frame - pts[i - 1].frame > 3) continue
        // skip jumps longer than 8% of the frame width: one of the two points is a false detection
        if (Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y) > JUMP * video.videoWidth) continue
        const alpha = i / pts.length
        const [x0, y0] = px(pts[i - 1])
        const [x1, y1] = px(pts[i])
        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(x1, y1)
        ctx.strokeStyle = EDGE
        ctx.globalAlpha = alpha
        ctx.lineWidth = 6
        ctx.stroke()
        ctx.strokeStyle = BALL
        ctx.lineWidth = 3
        ctx.stroke()
      }
      ctx.globalAlpha = 1
      const last = pts[pts.length - 1]
      if (last && last.frame === now) {
        const [x, y] = px(last)
        ctx.beginPath()
        ctx.arc(x, y, 9, 0, Math.PI * 2)
        ctx.strokeStyle = EDGE
        ctx.lineWidth = 5
        ctx.stroke()
        ctx.strokeStyle = BALL
        ctx.lineWidth = 2.5
        ctx.stroke()
      }
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [clock, fps])

  return <canvas ref={canvas} aria-hidden className="pointer-events-none absolute inset-0 size-full" />
}
