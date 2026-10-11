import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { PRESETS, cornersFrom, courtSegments, plausible, type Preset, type Pt } from '../court/homography'
import { useClock } from '../playback/clock'
import { letterbox } from './overlay'

const MARK = '#7fe3ff'
const EDGE = 'rgba(0, 0, 0, 0.75)'

/** Click four known court points on the paused video: the corners, or the near half when the camera stands
 *  behind an end line and the far corners are hidden. Points are kept in video pixels. */
export function CornerPicker({ saving, error, onSave, onCancel }: {
  saving: boolean
  error: string | null
  onSave: (points: Pt[], preset: Preset) => void
  onCancel: () => void
}) {
  const clock = useClock()
  const root = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const [points, setPoints] = useState<Pt[]>([])
  const [preset, setPreset] = useState<Preset>('corners')
  const video = clock.video()
  const size = { w: video?.videoWidth ?? 0, h: video?.videoHeight ?? 0 }
  const done = points.length === 4
  const corners = done ? cornersFrom(points, PRESETS[preset].court) : null
  const ok = corners !== null && plausible(corners, size.w, size.h)

  useEffect(() => root.current?.focus(), [])

  useEffect(() => {
    const el = canvas.current
    const ctx = el?.getContext('2d')
    if (!el || !ctx) return
    const dpr = window.devicePixelRatio || 1
    el.width = Math.round(el.clientWidth * dpr)
    el.height = Math.round(el.clientHeight * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, el.clientWidth, el.clientHeight)
    const lb = letterbox(size.w, size.h, el.clientWidth, el.clientHeight)
    if (!lb.scale) return
    const px = ([x, y]: Pt): Pt => [lb.x + x * lb.scale, lb.y + y * lb.scale]
    const segments: [Pt, Pt][] = ok && corners ? courtSegments(corners) : points.map((p, i) => [p, points[(i + 1) % points.length]] as [Pt, Pt]).slice(0, done ? 4 : points.length - 1)
    for (const [a, b] of segments) {
      const [ax, ay] = px(a)
      const [bx, by] = px(b)
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.strokeStyle = EDGE
      ctx.lineWidth = 4
      ctx.stroke()
      ctx.strokeStyle = MARK
      ctx.lineWidth = 2
      ctx.stroke()
    }
    ctx.font = '600 12px ui-monospace, monospace'
    points.forEach((p, i) => {
      const [x, y] = px(p)
      ctx.beginPath()
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fillStyle = EDGE
      ctx.fill()
      ctx.strokeStyle = MARK
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.fillStyle = MARK
      ctx.fillText(String(i + 1), x + 9, y - 7)
    })
  }, [points, ok, done, corners, size.w, size.h])

  const place = (e: PointerEvent<HTMLDivElement>) => {
    if (done || !size.w) return
    const r = e.currentTarget.getBoundingClientRect()
    const lb = letterbox(size.w, size.h, r.width, r.height)
    const x = (e.clientX - r.left - lb.x) / lb.scale
    const y = (e.clientY - r.top - lb.y) / lb.scale
    if (x < 0 || y < 0 || x > size.w || y > size.h) return // on the letterbox bars
    setPoints([...points, [Math.round(x), Math.round(y)]])
  }

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') onCancel()
    else if (e.key === 'Backspace') setPoints(points.slice(0, -1))
    else if (e.key === 'Enter' && ok && !saving) onSave(points, preset)
    else return
    e.preventDefault()
    e.stopPropagation()
  }

  return (
    <div ref={root} tabIndex={-1} onKeyDown={onKey} className="absolute inset-0 outline-none" aria-label="Court corners">
      <div onPointerDown={place} className="absolute inset-0 cursor-crosshair">
        <canvas ref={canvas} aria-hidden className="pointer-events-none size-full" />
      </div>
      <div className="absolute inset-x-2 top-2 flex flex-wrap items-center gap-2 rounded-md bg-window/95 px-3 py-2 text-[13px] shadow-[var(--shadow-window)]">
        <p className="mr-auto" aria-live="polite">
          {done
            ? ok ? 'Check the lines, then save.' : 'These corners do not form a court. Press Backspace to move the last one.'
            : <>Click the <strong>{PRESETS[preset].steps[points.length]}</strong> ({points.length + 1} of 4).{preset === 'corners' ? ' Far is the sideline away from the camera.' : points.length < 2 ? ' The centre line is on the floor where the net posts stand, not the bottom of the net.' : ''}</>}
          {error && <span className="ml-2 text-review">{error}</span>}
        </p>
        <label className="flex items-center gap-1.5">
          <span className="text-ink-muted">Points</span>
          <select className="rounded border border-line bg-window px-1 py-0.5" value={preset}
            onChange={(e) => { setPreset(e.target.value as Preset); setPoints([]) }}>
            <option value="corners">Four corners</option>
            <option value="near_half">Near half (camera behind an end line)</option>
          </select>
        </label>
        <button type="button" className="rounded border border-line px-2 py-0.5" onClick={() => setPoints(points.slice(0, -1))} disabled={!points.length}>
          Undo
        </button>
        <button type="button" className="rounded border border-line px-2 py-0.5" onClick={onCancel}>Cancel</button>
        <button type="button" className="rounded border border-accent bg-panel px-2 py-0.5 font-semibold disabled:opacity-50"
          disabled={!ok || saving} onClick={() => onSave(points, preset)}>
          {saving ? 'Saving…' : 'Save court'}
        </button>
      </div>
    </div>
  )
}
