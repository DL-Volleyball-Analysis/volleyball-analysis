import type { StageInfo } from '../api/types'
import { STAGE_LABEL } from '../ui/format'

const STATUS: Record<StageInfo['status'], string> = {
  done: 'Done',
  unavailable: 'Not available yet',
  todo: 'Not implemented yet',
  pending: 'Pending',
}

export function StagePanel({ stages }: { stages: readonly StageInfo[] }) {
  return (
    <ol aria-label="Analysis stages">
      {stages.map((s) => (
        <li key={s.name} className="border-b border-line py-2">
          <div className="flex justify-between gap-3">
            <span>{STAGE_LABEL[s.name]}</span>
            <span className={s.status === 'done' ? 'text-ink-muted' : 'text-review'}>{STATUS[s.status]}</span>
          </div>
          {s.message && <p className="mt-0.5 text-[13px] text-ink-muted">{s.message}</p>}
        </li>
      ))}
    </ol>
  )
}
