import { useEffect, useRef } from 'react'
import type { Rally } from '../api/types'
import { TeamMark } from '../ui/TeamMark'
import { formatDuration } from '../ui/format'
import { needsReview, reasonText } from './rallyText'

// The time column gives way on narrow screens so the end reason stays readable.
const COLS = 'grid grid-cols-[2rem_3.5rem_1fr_3.25rem] sm:grid-cols-[2rem_3.5rem_1fr_3rem_3.25rem] items-center gap-x-2 px-2'

export function RallyList({ rallies, currentIndex, onSelect }: {
  rallies: readonly Rally[]
  currentIndex: number
  onSelect: (r: Rally) => void
}) {
  const list = useRef<HTMLOListElement>(null)
  const current = useRef<HTMLButtonElement>(null)
  // Keep the current rally visible by scrolling the list only; scrollIntoView would also
  // scroll the page whenever the playhead moves.
  useEffect(() => {
    const box = list.current
    const row = current.current?.parentElement
    if (!box || !row) return
    if (row.offsetTop < box.scrollTop) box.scrollTop = row.offsetTop
    else if (row.offsetTop + row.offsetHeight > box.scrollTop + box.clientHeight) {
      box.scrollTop = row.offsetTop + row.offsetHeight - box.clientHeight
    }
  }, [currentIndex])

  if (rallies.length === 0) return <p className="text-ink-muted">No rallies found yet.</p>
  return (
    <div>
      <div aria-hidden className={`${COLS} border-b border-line pb-1.5 text-[13px] text-ink-muted`}>
        <span>#</span>
        <span>Winner</span>
        <span>End</span>
        <span className="hidden text-right sm:block">Time</span>
        <span className="text-right">Conf.</span>
      </div>
      <ol ref={list} className="relative max-h-[26rem] overflow-y-auto" aria-label="Rallies">
        {rallies.map((r, i) => {
          const isCurrent = i === currentIndex
          const label = [
            `Rally ${r.idx + 1}`,
            r.effective_winner ? `won by ${r.effective_winner.toUpperCase()}` : 'winner unknown',
            reasonText(r),
            `at ${formatDuration(r.start_s)}`,
            r.confidence == null ? null : `confidence ${Math.round(r.confidence * 100)}%`,
            r.winner_override != null ? 'edited' : null,
            needsReview(r) ? 'needs review' : null,
          ].filter(Boolean).join(', ')
          return (
            <li key={r.idx} className="border-b border-line">
              <button
                ref={isCurrent ? current : undefined}
                type="button"
                onClick={() => onSelect(r)}
                aria-label={label}
                aria-current={isCurrent ? 'true' : undefined}
                className={`${COLS} w-full border-l-2 py-1.5 text-left ${isCurrent ? 'border-accent bg-panel' : 'border-transparent hover:bg-panel'}`}
              >
                <span className="text-ink-muted">{r.idx + 1}</span>
                <span>{r.effective_winner ? <TeamMark team={r.effective_winner} /> : <span className="text-ink-muted">–</span>}</span>
                <span className="truncate">
                  {reasonText(r)}
                  {r.winner_override != null && <span className="ml-2 text-[13px] text-ink-muted">edited</span>}
                </span>
                <span className="hidden text-right font-mono text-[12px] text-ink-muted sm:block">{formatDuration(r.start_s)}</span>
                <span className="text-right">
                  {needsReview(r) && (
                    <span className="mr-1 text-review" title="Low confidence: check this rally">
                      ▲<span className="sr-only">Review</span>
                    </span>
                  )}
                  <span className={needsReview(r) ? 'text-review' : 'text-ink-muted'}>
                    {r.confidence == null ? '' : Math.round(r.confidence * 100)}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
