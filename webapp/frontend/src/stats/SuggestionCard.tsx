import { useState } from 'react'
import type { Suggestion, Team } from '../api/types'
import { formatTimecode } from '../ui/format'
import { KIND_LABEL } from './tagText'

/** A tag proposed from an action event. Accepting posts an ordinary tag (the same as typing it); nothing counts
 * before that. Team and number are prefilled when the system knows them and must be given when it does not. */
export function SuggestionCard({ suggestion, saving, onAccept, onDismiss, onClose }: {
  suggestion: Suggestion
  saving?: boolean
  onAccept: (team: Team, number: number) => void
  onDismiss: () => void
  onClose: () => void
}) {
  const [team, setTeam] = useState<Team | ''>(suggestion.team ?? '')
  const [number, setNumber] = useState(suggestion.number != null ? String(suggestion.number) : '')
  const n = Number(number)
  const valid = team !== '' && number !== '' && Number.isInteger(n) && n >= 0 && n <= 99
  const button = 'rounded border border-line px-2 py-0.5 font-medium hover:bg-panel disabled:opacity-50'
  return (
    <section aria-label="Suggested tag" className="text-[13px]">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="font-semibold">Suggested {KIND_LABEL[suggestion.kind].toLowerCase()}</h2>
        <button type="button" className="text-ink-muted hover:text-ink" onClick={onClose}>Close</button>
      </div>
      <p className="mb-2 text-[12px] text-ink-muted">
        From the action model at <span className="font-mono">{formatTimecode(suggestion.time_s)}</span>. Not counted until accepted.
      </p>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => { e.preventDefault(); if (valid) onAccept(team as Team, n) }}
      >
        <label className="flex flex-col gap-0.5">
          <span className="text-ink-muted">Team</span>
          <select className="rounded border border-line bg-window px-1 py-0.5" value={team} onChange={(e) => setTeam(e.target.value as Team | '')}>
            <option value="">choose</option>
            <option value="a">A</option>
            <option value="b">B</option>
          </select>
        </label>
        <label className="flex flex-col gap-0.5">
          <span className="text-ink-muted">Number</span>
          <input className="w-16 rounded border border-line bg-window px-1 py-0.5 font-mono" inputMode="numeric"
            value={number} onChange={(e) => setNumber(e.target.value.replace(/\D/g, '').slice(0, 2))} />
        </label>
        <button type="submit" className={button} disabled={!valid || saving}>Accept</button>
        <button type="button" className={button} onClick={onDismiss}>Dismiss</button>
      </form>
      {suggestion.number == null && <p className="mt-1 text-[12px] text-review">Shirt number not read: give it to accept.</p>}
    </section>
  )
}
