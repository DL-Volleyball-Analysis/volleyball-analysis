import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { useBallCoverage } from '../api/queries'
import type { ActionEvent, Rally, Suggestion, Tag } from '../api/types'
import { isIn } from '../court/geometry'
import { useClock } from '../playback/clock'
import { tagLabel } from '../stats/tagText'
import { formatDuration } from '../ui/format'
import { needsReview, reasonText } from './rallyText'
import { rulerStep, timeAt } from './timeline'

const LANES = ['Rallies', 'Ball', 'Landings', 'Actions', 'Tags', 'Review'] as const
const ACTION_SHORT: Record<ActionEvent['action'], string> = { serve: 'Srv', receive: 'Rec', set: 'Set', spike: 'Spk', block: 'Blk' }
const LABEL_PX = 56 // room per ruler label, so labels never overlap on narrow screens

/**
 * Editor-style timeline: a ruler and six lanes (rallies by winner, ball detection coverage,
 * landings, recognised actions, attack / serve tags with open suggestions, rallies to review) with a playhead. The playhead moves in an animation frame from the
 * video's own time, outside React; click or drag on a lane to seek.
 */
export function MatchTimeline({ videoId, rallies, duration, currentIndex, onSelect, tags = [], selectedTag, onSelectTag,
  actions = [], suggestions = [], selectedSuggestion, onSelectSuggestion }: {
  videoId: string
  rallies: readonly Rally[]
  duration: number
  currentIndex: number
  onSelect: (r: Rally) => void
  tags?: readonly Tag[]
  selectedTag?: string | null
  onSelectTag?: (t: Tag) => void
  actions?: readonly ActionEvent[]
  suggestions?: readonly Suggestion[]
  selectedSuggestion?: string | null
  onSelectSuggestion?: (s: Suggestion) => void
}) {
  const clock = useClock()
  const track = useRef<HTMLDivElement>(null)
  const playhead = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const coverage = useBallCoverage(videoId)
  const [trackWidth, setTrackWidth] = useState(800)

  // Re-measure on resize only (not during playback) to choose how many ruler labels fit.
  useEffect(() => {
    const el = track.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([entry]) => setTrackWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    let frame = 0
    const move = () => {
      const t = clock.video()?.currentTime ?? 0
      if (playhead.current && duration) playhead.current.style.left = `${(100 * Math.min(t, duration)) / duration}%`
      frame = requestAnimationFrame(move)
    }
    frame = requestAnimationFrame(move)
    return () => cancelAnimationFrame(frame)
  }, [clock, duration])

  if (!duration) return null
  const pct = (s: number) => `${(100 * s) / duration}%`
  const step = rulerStep(duration, Math.max(2, Math.floor(trackWidth / LABEL_PX)))
  const ticks = Array.from({ length: Math.floor(duration / step) + 1 }, (_, i) => i * step)

  const seekAt = (e: PointerEvent) => {
    if (track.current) clock.seek(timeAt(e.clientX, track.current.getBoundingClientRect(), duration))
  }
  const onDown = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest('button')) return // rally blocks select their rally
    dragging.current = true
    e.currentTarget.setPointerCapture?.(e.pointerId)
    seekAt(e)
  }

  return (
    <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] text-[12px]" role="group" aria-label="Match timeline">
      <div className="border-r border-line bg-panel">
        <div className="h-5" />
        {LANES.map((l) => (
          <div key={l} className="flex h-6 items-center px-2 text-ink-muted">{l}</div>
        ))}
      </div>
      <div
        ref={track}
        className="relative cursor-text select-none"
        data-testid="timeline-track"
        onPointerDown={onDown}
        onPointerMove={(e) => dragging.current && seekAt(e)}
        onPointerUp={() => { dragging.current = false }}
        onPointerCancel={() => { dragging.current = false }}
      >
        <div className="relative h-5 border-b border-line">
          {ticks.map((t) => (
            <span key={t} className="absolute top-0.5 -translate-x-1/2 font-mono text-[11px] text-ink-muted first:translate-x-0" style={{ left: pct(t) }}>
              {formatDuration(t)}
            </span>
          ))}
        </div>

        {/* Rallies: A above the centre line, B below */}
        <div className="relative h-6 border-b border-line">
          <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
          {rallies.map((r, i) => {
            const team = r.effective_winner
            const pos = team === 'a' ? 'top-0.5 bottom-1/2' : team === 'b' ? 'top-1/2 bottom-0.5' : 'top-1/4 bottom-1/4'
            const tone = team === 'a' ? 'bg-team-a' : team === 'b' ? 'bg-team-b' : 'bg-mute'
            const label = `Rally ${r.idx + 1}, ${team ? `won by ${team.toUpperCase()}` : 'winner unknown'}, ${reasonText(r)}${needsReview(r) ? ', needs review' : ''}`
            return (
              <button
                key={r.idx}
                type="button"
                title={label}
                aria-label={label}
                aria-current={i === currentIndex ? 'true' : undefined}
                onClick={() => onSelect(r)}
                className={`absolute min-w-1 rounded-[2px] ${pos} ${tone} ${i === currentIndex ? 'outline-2 outline-offset-1 outline-accent' : 'opacity-70 hover:opacity-100'}`}
                style={{ left: pct(r.start_s), width: pct(r.end_s - r.start_s) }}
              />
            )
          })}
        </div>

        {/* Ball: share of frames with a detection, per bin */}
        <div className="relative h-6 border-b border-line" data-testid="lane-ball">
          {coverage.data && (
            <svg className="absolute inset-0 size-full" viewBox={`0 0 ${coverage.data.coverage.length} 1`} preserveAspectRatio="none" aria-hidden>
              {coverage.data.coverage.map((c, i) => (
                <rect key={i} x={i} y={1 - c} width={1} height={c} fill="var(--lane-ball)" />
              ))}
            </svg>
          )}
          {coverage.isError && <span className="absolute inset-y-0 left-2 flex items-center text-ink-muted">Not tracked yet</span>}
        </div>

        {/* Landings: dot = in, cross = out, at the rally's end */}
        <div className="relative h-6 border-b border-line" data-testid="lane-landings">
          {rallies.filter((r) => r.landing_x != null && r.landing_y != null).map((r) => {
            const inside = isIn(r.landing_x!, r.landing_y!)
            return (
              <span
                key={r.idx}
                data-testid={inside ? 'landing-in' : 'landing-out'}
                title={`Rally ${r.idx + 1}: ${inside ? 'in' : 'out'}`}
                className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 leading-none text-lane-landing"
                style={{ left: pct(r.end_s) }}
              >
                {inside ? '●' : '×'}
              </span>
            )
          })}
        </div>

        {/* Actions: recognised by the action model, in the team's colour when known; click to seek */}
        <div className="relative h-6 border-b border-line" data-testid="lane-actions">
          {actions.map((a, i) => {
            const who = a.number != null ? `#${a.number}` : a.track_id != null ? `ID ${a.track_id}` : 'unknown player'
            const label = `${a.action} by ${who}${a.team ? ` (${a.team.toUpperCase()})` : ''} at ${a.start_s.toFixed(1)} s`
            return (
              <button
                key={i}
                type="button"
                data-testid="action-mark"
                title={label}
                aria-label={label}
                onClick={() => clock.seek(a.start_s)}
                className={`absolute top-1/2 -translate-y-1/2 rounded-[2px] px-0.5 font-mono text-[10px] leading-none ${a.team === 'a' ? 'text-team-a' : a.team === 'b' ? 'text-team-b' : 'text-ink-muted'}`}
                style={{ left: pct(a.start_s) }}
              >
                {ACTION_SHORT[a.action]}
              </button>
            )
          })}
        </div>

        {/* Tags: the player number (S before it for a serve) in the team's colour; outside rallies dimmed.
            Open suggestions are dashed and never counted until accepted. */}
        <div className="relative h-6 border-b border-line" data-testid="lane-tags">
          {suggestions.filter((s) => s.status === 'open').map((s) => {
            const label = `Suggested ${s.kind}${s.number != null ? ` by ${s.number}` : ''} at ${s.time_s.toFixed(1)} s`
            return (
              <button
                key={s.id}
                type="button"
                data-testid="suggestion-mark"
                title={label}
                aria-label={label}
                aria-pressed={s.id === selectedSuggestion}
                onClick={() => onSelectSuggestion?.(s)}
                className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[2px] border border-dashed border-ink-muted px-0.5 font-mono text-[11px] leading-none text-ink-muted ${s.id === selectedSuggestion ? 'outline-2 outline-offset-1 outline-accent' : ''}`}
                style={{ left: pct(s.time_s) }}
              >
                {s.kind === 'serve' ? 'S' : ''}{s.number ?? '?'}
              </button>
            )
          })}
          {tags.map((t) => (
            <button
              key={t.id}
              type="button"
              data-testid="tag-mark"
              title={tagLabel(t)}
              aria-label={tagLabel(t)}
              aria-pressed={t.id === selectedTag}
              onClick={() => onSelectTag?.(t)}
              className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[2px] px-0.5 font-mono text-[11px] font-semibold leading-none ${t.team === 'a' ? 'text-team-a' : 'text-team-b'} ${t.id === selectedTag ? 'outline-2 outline-offset-1 outline-accent' : ''} ${t.rally_idx == null ? 'opacity-50' : ''}`}
              style={{ left: pct(t.time_s) }}
            >
              {t.kind === 'serve' ? 'S' : ''}{t.number}
            </button>
          ))}
        </div>

        {/* Review: low-confidence rallies */}
        <div className="relative h-6">
          {rallies.filter(needsReview).map((r) => (
            <button
              key={r.idx}
              type="button"
              data-testid="review-mark"
              aria-label={`Review rally ${r.idx + 1}`}
              onClick={() => onSelect(r)}
              className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 leading-none text-review"
              style={{ left: pct((r.start_s + r.end_s) / 2) }}
            >
              ▲
            </button>
          ))}
        </div>

        <div ref={playhead} aria-hidden data-testid="playhead" className="pointer-events-none absolute inset-y-0 w-px bg-ink" style={{ left: 0 }} />
      </div>
    </div>
  )
}
