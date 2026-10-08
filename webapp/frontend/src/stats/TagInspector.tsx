import type { Outcome, Tag } from '../api/types'
import { TeamMark } from '../ui/TeamMark'
import { formatTimecode } from '../ui/format'
import { KIND_LABEL, OUTCOMES, OUTCOME_LABEL } from './tagText'

/** The selected tag: outcome (automatic or set by the user) and delete. */
export function TagInspector({ tag, onOutcome, onDelete, onClose }: {
  tag: Tag
  onOutcome: (outcome: Outcome | null) => void
  onDelete: () => void
  onClose: () => void
}) {
  const button = 'rounded border border-line px-2 py-0.5 font-medium hover:bg-panel'
  return (
    <section aria-label="Selected tag" className="text-[13px]">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="font-semibold">
          {KIND_LABEL[tag.kind]} <TeamMark team={tag.team} /> {tag.number}
        </h2>
        <button type="button" className="text-ink-muted hover:text-ink" onClick={onClose}>Close</button>
      </div>
      <dl>
        <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] border-b border-line py-1.5">
          <dt className="text-ink-muted">Time</dt>
          <dd className="font-mono text-[12px]">{formatTimecode(tag.time_s)}</dd>
        </div>
        <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] border-b border-line py-1.5">
          <dt className="text-ink-muted">Rally</dt>
          <dd>{tag.rally_idx == null ? <span className="text-review">outside rallies, not counted</span> : tag.rally_idx + 1}</dd>
        </div>
        <div className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center border-b border-line py-1.5">
          <dt className="text-ink-muted">Outcome</dt>
          <dd>
            <label className="sr-only" htmlFor="tag-outcome">Outcome</label>
            <select
              id="tag-outcome"
              className="rounded border border-line bg-window px-1 py-0.5"
              value={tag.outcome ?? ''}
              onChange={(e) => onOutcome((e.target.value || null) as Outcome | null)}
            >
              <option value="">Automatic: {OUTCOME_LABEL[tag.effective_outcome]}</option>
              {OUTCOMES[tag.kind].map((o) => (
                <option key={o} value={o}>{OUTCOME_LABEL[o]}</option>
              ))}
            </select>
          </dd>
        </div>
      </dl>
      <p className="mt-1 text-[12px] text-ink-muted">
        Automatic: the last tag of a rally takes its outcome from the winner; earlier tags are in play.
      </p>
      <div className="mt-2">
        <button type="button" className={button} onClick={onDelete}>Delete tag</button>
      </div>
    </section>
  )
}
