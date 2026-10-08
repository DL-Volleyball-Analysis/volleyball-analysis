import type { ReactNode } from 'react'
import type { Rally, Team } from '../api/types'
import { isIn } from '../court/geometry'
import { TeamMark } from '../ui/TeamMark'
import { formatTimecode } from '../ui/format'
import { needsReview, reasonText } from './rallyText'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-baseline border-b border-line py-1.5">
      <dt className="text-ink-muted">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

/** Properties of the rally at the playhead, editor-style, with the winner correction. */
export function RallyInspector({ rallies, index, onCorrect }: {
  rallies: readonly Rally[]
  index: number
  onCorrect: (idx: number, winner: Team | null) => void
}) {
  const r = rallies[index]
  if (!r) return <p className="py-2 text-ink-muted">{rallies.length ? 'Before the first rally.' : 'No rallies yet.'}</p>
  const landed = r.landing_x != null && r.landing_y != null
  const button = 'rounded border border-line px-2 py-0.5 font-medium hover:bg-panel'
  return (
    <section aria-label="Current rally">
      <dl className="text-[13px]">
        <Row label="Rally">
          {r.idx + 1} <span className="text-ink-muted">of {rallies.length}</span>
        </Row>
        <Row label="Time">
          <span className="font-mono text-[12px]">{formatTimecode(r.start_s)} – {formatTimecode(r.end_s)}</span>
        </Row>
        <Row label="Winner">
          {r.effective_winner ? <TeamMark team={r.effective_winner} /> : <span className="text-ink-muted">unknown</span>}
          {r.winner_override != null && (
            <span className="ml-2 text-ink-muted">
              edited{r.winner ? `, model said ${r.winner.toUpperCase()}` : ''}
            </span>
          )}
        </Row>
        <Row label="End">{reasonText(r)}</Row>
        <Row label="Confidence">
          {r.confidence == null ? (
            <span className="text-ink-muted">–</span>
          ) : (
            <span className={needsReview(r) ? 'text-review' : ''}>
              {Math.round(r.confidence * 100)}%{needsReview(r) && ' ▲ check this rally'}
            </span>
          )}
        </Row>
        <Row label="Landing">
          {landed ? (
            <>
              <span className="font-mono text-[12px]">
                x {r.landing_x!.toFixed(1)} m, y {r.landing_y!.toFixed(1)} m
              </span>
              <span className="ml-2 text-ink-muted">{isIn(r.landing_x!, r.landing_y!) ? 'in' : 'out'}</span>
            </>
          ) : (
            <span className="text-ink-muted">–</span>
          )}
        </Row>
      </dl>
      <div className="mt-2 flex items-center gap-2 text-[13px]">
        <span className="mr-1 text-ink-muted">Set winner</span>
        <button type="button" className={button} onClick={() => onCorrect(r.idx, 'a')}>
          <span className="text-team-a">A</span>
        </button>
        <button type="button" className={button} onClick={() => onCorrect(r.idx, 'b')}>
          <span className="text-team-b">B</span>
        </button>
        <button type="button" className={button} disabled={r.winner_override == null} onClick={() => onCorrect(r.idx, null)}>
          Clear
        </button>
      </div>
    </section>
  )
}
