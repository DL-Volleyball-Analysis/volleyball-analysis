import { useState } from 'react'
import type { RosterPlayer, Team } from '../api/types'
import { TeamMark } from '../ui/TeamMark'

type Row = { number: string; name: string }

const toRows = (players: readonly RosterPlayer[], team: Team): Row[] =>
  players.filter((p) => p.team === team).map((p) => ({ number: String(p.number), name: p.name ?? '' }))

/** Both teams' numbers and names; the server rejects a number listed twice in a team. */
export function RosterEditor({ players, saving, error, onSave, onCancel }: {
  players: readonly RosterPlayer[]
  saving?: boolean
  error?: string
  onSave: (players: RosterPlayer[]) => void
  onCancel: () => void
}) {
  const [rows, setRows] = useState<Record<Team, Row[]>>({ a: toRows(players, 'a'), b: toRows(players, 'b') })
  const set = (team: Team, i: number, patch: Partial<Row>) =>
    setRows((r) => ({ ...r, [team]: r[team].map((row, j) => (j === i ? { ...row, ...patch } : row)) }))
  const add = (team: Team) => setRows((r) => ({ ...r, [team]: [...r[team], { number: '', name: '' }] }))
  const remove = (team: Team, i: number) => setRows((r) => ({ ...r, [team]: r[team].filter((_, j) => j !== i) }))

  function save() {
    const out: RosterPlayer[] = []
    for (const team of ['a', 'b'] as Team[]) {
      for (const row of rows[team]) {
        if (row.number === '') continue
        out.push({ team, number: Number(row.number), name: row.name.trim() || null })
      }
    }
    onSave(out)
  }

  const input = 'rounded border border-line bg-window px-1.5 py-0.5'
  return (
    <section aria-label="Roster" className="space-y-3 text-[13px]">
      {(['a', 'b'] as Team[]).map((team) => (
        <fieldset key={team}>
          <legend className="mb-1 font-semibold">Team <TeamMark team={team} /></legend>
          <ul className="space-y-1">
            {rows[team].map((row, i) => (
              <li key={i} className="flex items-center gap-2">
                <input
                  aria-label={`Team ${team.toUpperCase()} player ${i + 1} number`}
                  inputMode="numeric"
                  className={`${input} w-14 font-mono`}
                  value={row.number}
                  onChange={(e) => set(team, i, { number: e.target.value.replace(/\D/g, '').slice(0, 2) })}
                />
                <input
                  aria-label={`Team ${team.toUpperCase()} player ${i + 1} name`}
                  placeholder="Name (optional)"
                  className={`${input} min-w-0 flex-1`}
                  value={row.name}
                  onChange={(e) => set(team, i, { name: e.target.value })}
                />
                <button type="button" className="text-ink-muted hover:text-ink" onClick={() => remove(team, i)}
                  aria-label={`Remove team ${team.toUpperCase()} player ${i + 1}`}>Remove</button>
              </li>
            ))}
          </ul>
          <button type="button" className="mt-1 text-accent hover:underline" onClick={() => add(team)}>Add player</button>
        </fieldset>
      ))}
      {error && <p role="alert" className="text-review">{error}</p>}
      <div className="flex gap-2">
        <button type="button" className="rounded bg-accent px-3 py-1 font-medium text-on-accent" disabled={saving} onClick={save}>
          {saving ? 'Saving…' : 'Save roster'}
        </button>
        <button type="button" className="rounded border border-line px-3 py-1" onClick={onCancel}>Cancel</button>
      </div>
    </section>
  )
}
