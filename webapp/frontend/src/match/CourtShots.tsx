import type { Court, CourtShotInfo } from '../api/types'
import { formatTimecode } from '../ui/format'

const STATUS: Record<CourtShotInfo['status'], string> = {
  ok: 'Court found',
  needs_review: 'Doubtful, not used',
  failed: 'Not found',
}

/** The court of each camera shot, and the way to set it by hand when the model is wrong or doubtful. */
export function CourtShots({ court, busy, onSet, onClear }: {
  court: Court | undefined
  busy: boolean
  onSet: (shot: CourtShotInfo) => void
  onClear: (shot: CourtShotInfo) => void
}) {
  if (!court || court.status !== 'done') {
    return <p className="py-2 text-[13px] text-ink-muted">Court corners can be set once the court stage has run.</p>
  }
  const fps = court.fps ?? 30
  return (
    <section aria-labelledby="court-shots" className="mt-3">
      <h3 id="court-shots" className="text-[13px] font-semibold">Court per camera shot</h3>
      <p className="mb-1 text-[12px] text-ink-muted">
        Players, landings and 3D flights use a shot only when its court is found. Set the corners by hand to use a doubtful one.
      </p>
      <ol>
        {court.shots.map((s) => (
          <li key={s.shot} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line py-1.5 text-[13px]">
            <span className="font-mono text-[12px] text-ink-muted">
              {formatTimecode(s.start_frame / fps)}–{formatTimecode(s.end_frame / fps)}
            </span>
            <span className={s.status === 'ok' ? '' : 'text-review'}>
              {s.corrected ? 'Set by you' : STATUS[s.status]}
            </span>
            <span className="ml-auto flex gap-2">
              {s.corrected && (
                <button type="button" className="rounded border border-line px-2 py-0.5" disabled={busy} onClick={() => onClear(s)}>
                  Clear
                </button>
              )}
              <button type="button" className="rounded border border-line px-2 py-0.5" disabled={busy} onClick={() => onSet(s)}>
                Set corners
              </button>
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
