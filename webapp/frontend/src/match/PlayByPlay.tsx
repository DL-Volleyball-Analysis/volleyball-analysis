import { useEffect, useState } from 'react'
import type { ActionEvent, Rally } from '../api/types'
import { useClock } from '../playback/clock'
import { TeamMark } from '../ui/TeamMark'
import { formatTimecode } from '../ui/format'
import { CLIP_LEAD_S, advance, playerKey, playerOf } from './playlist'

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
  const [player, setPlayer] = useState('')
  // While the list plays: the queue frozen when Play was pressed (playback re-renders the page and moves the rally,
  // which must not change it) and the clip being played. Each clip runs from CLIP_LEAD_S before the action to
  // CLIP_TAIL_S after it, then the next; pausing the video stops the list.
  const [queue, setQueue] = useState<{ list: readonly ActionEvent[]; at: number; seek: boolean } | null>(null)
  const playing = queue?.at ?? null
  const list = filtered(actions, rally, whole, kind, player)
  useEffect(() => {
    const video = clock.video()
    if (!queue || !video) return
    const onTime = () => {
      const next = advance(queue.list, queue.at, video.currentTime)
      if (next === null) { setQueue(null); video.pause() } else if (next.at !== queue.at) setQueue({ list: queue.list, ...next })
    }
    const onPause = () => setQueue(null)
    video.addEventListener('timeupdate', onTime)
    video.addEventListener('pause', onPause)
    return () => { video.removeEventListener('timeupdate', onTime); video.removeEventListener('pause', onPause) }
  }, [clock, queue])
  useEffect(() => { // seek to a clip only when it does not follow on from the one playing
    const video = clock.video()
    if (!queue?.seek || !video) return
    clock.seek(queue.list[queue.at].start_s - CLIP_LEAD_S)
    if (video.paused) void video.play()
  }, [clock, queue])

  if (!rally && !whole) return null
  const inRally = filtered(actions, rally, whole, null, '')
  const shown = queue?.list ?? list
  const players = [...new Map(inRally.map((a) => [playerKey(a), a])).values()].sort((a, b) =>
    playerKey(a).localeCompare(playerKey(b), undefined, { numeric: true }))
  const chip = (k: Kind | null, label: string) => (
    <button key={label} type="button" aria-pressed={kind === k} onClick={() => { setKind(k); setQueue(null) }}
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
            <button key={String(w)} type="button" aria-pressed={whole === w} onClick={() => { setWhole(w); setQueue(null) }}
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
      <div className="mb-1.5 flex items-center gap-2 text-[12px]">
        <label className="flex items-center gap-1 text-ink-muted">
          Player
          <select value={player} onChange={(e) => { setPlayer(e.target.value); setQueue(null) }}
            className="rounded border border-line bg-window px-1 py-0.5 text-ink">
            <option value="">All</option>
            {players.map((a) => (
              <option key={playerKey(a)} value={playerKey(a)}>{playerOf(a)}{a.team ? ` (${a.team.toUpperCase()})` : ''}</option>
            ))}
          </select>
        </label>
        <button type="button" disabled={shown.length === 0}
          onClick={() => setQueue(queue ? null : { list, at: 0, seek: true })}
          className="ml-auto rounded border border-line px-1.5 py-0.5 hover:bg-panel disabled:opacity-50">
          {playing === null ? `▶ Play these (${shown.length})` : `■ Stop (${playing + 1} of ${shown.length})`}
        </button>
      </div>
      {shown.length === 0 ? (
        <p className="text-[13px] text-ink-muted">No actions recognised {whole ? 'in this match' : 'in this rally'}.</p>
      ) : (
        <ol className={whole ? 'max-h-64 overflow-y-auto' : undefined}>
          {shown.map((a, i) => {
            const who = playerOf(a)
            return (
              <li key={`${a.start_s}-${i}`} aria-current={playing === i ? 'true' : undefined}
                className={playing === i ? 'bg-panel' : undefined}>
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

/** Actions of the rally (or the whole match), of one kind and one player when chosen, in time order. */
function filtered(actions: readonly ActionEvent[], rally: Rally | undefined, whole: boolean, kind: Kind | null,
  player: string): ActionEvent[] {
  return actions
    .filter((a) => whole || (rally && a.start_s >= rally.start_s - MARGIN_S && a.start_s <= rally.end_s + MARGIN_S))
    .filter((a) => !kind || a.action === kind)
    .filter((a) => !player || playerKey(a) === player)
    .sort((a, b) => a.start_s - b.start_s)
}
