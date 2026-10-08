import { useState, type KeyboardEvent } from 'react'
import type { TagKind, Team } from '../api/types'
import { formatTimecode } from '../ui/format'
import { KIND_LABEL } from './tagText'

/**
 * Entry for one tag: digits type the player number, A / B switch the team, Enter saves, Esc cancels.
 * Letters pick the team because digits are the number (1 / 2 could not also mean team A / B).
 */
export function TagEntry({ kind, timeS, defaultTeam, saving, onSave, onCancel }: {
  kind: TagKind
  timeS: number
  defaultTeam: Team
  saving?: boolean
  onSave: (team: Team, number: number) => void
  onCancel: () => void
}) {
  const [team, setTeam] = useState<Team>(defaultTeam)
  const [number, setNumber] = useState('')

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    const k = e.key.toLowerCase()
    if (k === 'a' || k === 'b') {
      e.preventDefault()
      setTeam(k)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (number !== '') onSave(team, Number(number))
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onCancel()
    }
  }

  const teamButton = (t: Team) =>
    `rounded border px-2 py-0.5 font-semibold ${team === t ? 'border-accent bg-panel' : 'border-line'} ${t === 'a' ? 'text-team-a' : 'text-team-b'}`

  return (
    <section aria-label="New tag" className="rounded-md border border-accent/60 bg-panel p-3 text-[13px]">
      <p className="mb-2">
        <span className="font-semibold">{KIND_LABEL[kind]}</span>
        <span className="ml-2 font-mono text-[12px] text-ink-muted">at {formatTimecode(timeS)}</span>
      </p>
      <div className="flex items-center gap-2">
        <span className="text-ink-muted">Team</span>
        <button type="button" className={teamButton('a')} aria-pressed={team === 'a'} onClick={() => setTeam('a')}>A</button>
        <button type="button" className={teamButton('b')} aria-pressed={team === 'b'} onClick={() => setTeam('b')}>B</button>
        <label className="ml-2 flex items-center gap-2">
          <span className="text-ink-muted">Number</span>
          <input
            autoFocus
            inputMode="numeric"
            aria-label="Player number"
            className="w-14 rounded border border-line bg-window px-1.5 py-0.5 font-mono"
            value={number}
            onChange={(e) => setNumber(e.target.value.replace(/\D/g, '').slice(0, 2))}
            onKeyDown={onKey}
          />
        </label>
      </div>
      <p className="mt-2 text-[12px] text-ink-muted">
        <kbd>A</kbd> / <kbd>B</kbd> team, <kbd>Enter</kbd> {saving ? 'saving…' : 'save'}, <kbd>Esc</kbd> cancel
      </p>
    </section>
  )
}
