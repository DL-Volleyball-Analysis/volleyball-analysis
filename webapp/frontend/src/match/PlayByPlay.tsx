import { useState } from 'react'
import type { ActionEvent, Rally } from '../api/types'
import { useClock } from '../playback/clock'
import { TeamMark } from '../ui/TeamMark'
import { formatTimecode } from '../ui/format'

type Kind = ActionEvent['action']
const KINDS: readonly Kind[] = ['serve', 'receive', 'set', 'spike', 'block']
const NAME: Record<Kind, string> = { serve: 'Serve', receive: 'Receive', set: 'Set', spike: 'Attack', block: 'Block' }
const MARGIN_S = 0.5 // a serve toss or a last block can sit just outside the rally's detected span

/** The recognised actions of the current rally (or of the whole match) in order, filterable by kind; a row jumps the
 * video to that action. The timeline only shows where rallies are; this list says what happened (as Balltime's
 * actions list beside its player). */
export function PlayByPlay({ rally, actions }: { rally: Rally | undefined; actions: readonly ActionEvent[] }) {
  const clock = useClock()
  const [kind, setKind] = useState<Kind | null>(null)
  const [whole, setWhole] = useState(false)
  if (!rally && !whole) return null
  const inRally = actions
    .filter((a) => whole || (rally && a.start_s >= rally.start_s - MARGIN_S && a.start_s <= rally.end_s + MARGIN_S))
    .sort((a, b) => a.start_s - b.start_s)
  const shown = kind ? inRally.filter((a) => a.action === kind) : inRally
  const chip = (k: Kind | null, label: string) => (
    <button key={label} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
      className={`rounded border px-1.5 py-0.5 text-[12px] ${kind === k ? 'border-accent text-ink' : 'border-line text-ink-muted hover:text-ink'}`}>
      {label}
    </button>
  )
  return (
    <section aria-label="Play by play">
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <h3 className="text-[13px] font-semibold">Play by play</h3>
        <div role="group" aria-label="Actions of" className="flex gap-1 text-[12px]">
          {([false, true] as const).map((w) => (
            <button key={String(w)} type="button" aria-pressed={whole === w} onClick={() => setWhole(w)}
              className={`rounded px-1.5 py-0.5 ${whole === w ? 'bg-panel text-ink' : 'text-ink-muted hover:text-ink'}`}>
              {w ? 'Whole match' : 'This rally'}
            </button>
          ))}
        </div>
      </div>
      <p className="mb-1.5 text-[12px] text-ink-muted">
        Recognised from each player's pose; not yet matched to the ball's touches, so players in a ready position
        can appear together.
      </p>
      <div role="group" aria-label="Filter actions" className="mb-1.5 flex flex-wrap gap-1">
        {chip(null, 'All')}
        {KINDS.filter((k) => inRally.some((a) => a.action === k)).map((k) => chip(k, NAME[k]))}
      </div>
      {shown.length === 0 ? (
        <p className="text-[13px] text-ink-muted">No actions recognised {whole ? 'in this match' : 'in this rally'}.</p>
      ) : (
        <ol className={whole ? 'max-h-64 overflow-y-auto' : undefined}>
          {shown.map((a, i) => {
            const who = a.number != null ? `#${a.number}` : a.track_id != null ? `ID ${a.track_id}` : '–'
            return (
              <li key={`${a.start_s}-${i}`}>
                <button type="button" onClick={() => clock.seek(a.start_s)}
                  aria-label={`${NAME[a.action]} by ${who}${a.team ? ` of team ${a.team.toUpperCase()}` : ''} at ${formatTimecode(a.start_s)}`}
                  className="grid w-full grid-cols-[4.5rem_4.5rem_4.5rem_1.5rem] items-center border-b border-line py-1 text-left text-[13px] hover:bg-panel">
                  <span className="font-mono text-[12px] text-ink-muted">{formatTimecode(a.start_s)}</span>
                  <span>{NAME[a.action]}</span>
                  <span className="font-mono">{who}</span>
                  <span>{a.team ? <TeamMark team={a.team} /> : null}</span>
                </button>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
