import { useState } from 'react'
import { api } from '../api/client'
import { usePutRoster, useRoster, useStats } from '../api/queries'
import type { StatLine, Team } from '../api/types'
import { TeamMark } from '../ui/TeamMark'
import { RosterEditor } from './RosterEditor'
import { ratio, sets } from './statsText'

const COLS: { key: string; label: string; title: string }[] = [
  { key: 'attempts', label: 'Att', title: 'Attack attempts' },
  { key: 'kills', label: 'K', title: 'Kills' },
  { key: 'attack_errors', label: 'E', title: 'Attack errors' },
  { key: 'efficiency', label: 'Eff', title: 'Attack efficiency: (kills − errors) / decided attempts' },
  { key: 'kill_rate', label: 'K%', title: 'Kill rate: kills / decided attempts' },
  { key: 'serves', label: 'Srv', title: 'Serves' },
  { key: 'aces', label: 'Ace', title: 'Aces' },
  { key: 'serve_errors', label: 'SE', title: 'Serve errors' },
]

const RATIOS = new Set(['efficiency', 'kill_rate'])

function cell(line: StatLine, key: string): string {
  if (key === 'efficiency') return ratio(line.efficiency)
  if (key === 'kill_rate') return ratio(line.kill_rate)
  return String(line[key as keyof StatLine] ?? '')
}

/** The asterisk for a line with unknown outcomes; spoken as "incomplete". */
function Incomplete({ unknown }: { unknown: number }) {
  return (
    <>
      {' '}
      <span className="text-review" title={`${unknown} tag(s) without an outcome yet`}>
        *<span className="sr-only"> incomplete</span>
      </span>
    </>
  )
}

function TeamTable({ team, lines }: { team: Team; lines: StatLine[] }) {
  const players = lines.filter((l) => l.number != null)
  const total = lines.find((l) => l.number == null)
  if (!total) return null
  return (
    <table className="w-full table-fixed text-[12px]">
      <caption className="mb-1 text-left text-[13px] font-semibold">Team <TeamMark team={team} /></caption>
      {/* fixed widths, so both teams' columns line up: ratios (up to "-1.000") get more room than counts */}
      <colgroup>
        <col className="w-[22%]" />
        {COLS.map((c) => <col key={c.key} className={RATIOS.has(c.key) ? 'w-[14%]' : 'w-[8%]'} />)}
      </colgroup>
      <thead>
        <tr className="border-b border-line text-ink-muted">
          <th scope="col" className="py-1 text-left font-medium">Player</th>
          {COLS.map((c) => (
            <th key={c.key} scope="col" title={c.title} className="py-1 pl-1 text-right font-medium">
              <abbr title={c.title} className="no-underline">{c.label}</abbr>
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="font-mono">
        {players.map((l) => (
          <tr key={l.number} className="border-b border-line">
            <th scope="row" className="py-1 text-left font-sans font-normal">
              {l.number}
              {l.name && <>{' '}<span className="text-ink-muted">{l.name}</span></>}
              {l.incomplete && <Incomplete unknown={l.unknown} />}
            </th>
            {COLS.map((c) => <td key={c.key} className="py-1 pl-1 text-right">{cell(l, c.key)}</td>)}
          </tr>
        ))}
        <tr className="font-semibold">
          <th scope="row" className="py-1 text-left font-sans">Team{total.incomplete && <Incomplete unknown={total.unknown} />}</th>
          {COLS.map((c) => <td key={c.key} className="py-1 pl-1 text-right">{cell(total, c.key)}</td>)}
        </tr>
      </tbody>
    </table>
  )
}

/** Attack and serve statistics from the tags, per set or for the match, with the roster editor. */
export function StatsPanel({ videoId }: { videoId: string }) {
  const stats = useStats(videoId)
  const roster = useRoster(videoId)
  const putRoster = usePutRoster(videoId)
  const [setNo, setSetNo] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)

  if (editing && roster.data) {
    return (
      <RosterEditor
        players={roster.data.players}
        saving={putRoster.isPending}
        error={putRoster.isError ? putRoster.error.message : undefined}
        onSave={(players) => putRoster.mutate(players, { onSuccess: () => setEditing(false) })}
        onCancel={() => { putRoster.reset(); setEditing(false) }}
      />
    )
  }
  if (stats.isPending) return <p className="py-2 text-ink-muted">Loading…</p>
  if (stats.isError) return <p className="py-2 text-review">Could not load statistics: {stats.error.message}</p>

  const s = stats.data
  const lines = s.lines.filter((l) => l.set_no === setNo)
  const incomplete = lines.some((l) => l.incomplete)
  return (
    <div className="space-y-3 text-[13px]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <label className="flex items-center gap-1.5">
          <span className="text-ink-muted">Show</span>
          <select className="rounded border border-line bg-window px-1 py-0.5" value={setNo ?? ''}
            onChange={(e) => setSetNo(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Match</option>
            {sets(s.lines).map((n) => <option key={n} value={n}>Set {n}</option>)}
          </select>
        </label>
        <a className="text-accent hover:underline" href={api.statsCsvUrl(videoId)} download>Export CSV</a>
        <button type="button" className="text-accent hover:underline" onClick={() => setEditing(true)} disabled={!roster.data}>
          Edit roster
        </button>
      </div>
      <p className="text-[12px] text-ink-muted">
        {s.tagged_rallies} of {s.rallies} rallies tagged.
        {s.outside > 0 && ` ${s.outside} tag(s) outside rallies are not counted.`}
      </p>
      {lines.length === 0 ? (
        <p className="text-ink-muted">
          No tags yet. Press <kbd>T</kbd> at an attack or <kbd>S</kbd> at a serve, type the player number and press <kbd>Enter</kbd>.
          Tag every attack, not only the last one of a rally, or efficiency comes out too high.
        </p>
      ) : (
        <>
          {(['a', 'b'] as Team[]).map((team) => (
            <TeamTable key={team} team={team} lines={lines.filter((l) => l.team === team)} />
          ))}
          {incomplete && <p className="text-[12px] text-review">* includes rallies without a winner yet; their tags are left out of the ratios.</p>}
        </>
      )}
    </div>
  )
}
