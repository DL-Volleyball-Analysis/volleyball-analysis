import { Link } from 'react-router'
import { useStartJob } from '../api/queries'
import type { ScoreSummary, Video } from '../api/types'
import { BreakableName } from '../ui/BreakableName'
import { STAGE_LABEL, formatDuration } from '../ui/format'

function Progress({ video }: { video: Video }) {
  const job = video.job!
  const pct = Math.round(job.progress * 100)
  const label = job.status === 'queued' ? 'Waiting to analyse' : job.stage ? STAGE_LABEL[job.stage] : 'Starting'
  return (
    <div className="w-56">
      <div className="flex justify-between">
        <span>{label}</span>
        <span className="text-ink-muted">{pct}%</span>
      </div>
      <div className="mt-1 h-0.5 bg-line" role="progressbar" aria-label={label} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Failed({ video }: { video: Video }) {
  const start = useStartJob()
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-review">Analysis failed: {video.job?.error ?? 'unknown error'}</span>
      <button
        type="button"
        onClick={() => start.mutate({ id: video.id })}
        disabled={start.isPending}
        className="rounded border border-line px-2 py-0.5 font-medium hover:bg-panel"
      >
        Analyse again
      </button>
    </div>
  )
}

function Score({ score }: { score: ScoreSummary }) {
  // Each segment stays on one line; segments wrap as units on narrow screens.
  return (
    <span className="flex flex-wrap gap-x-3">
      <span className="whitespace-nowrap font-semibold">
        <span className="text-team-a">A</span> {score.sets_a}–{score.sets_b} <span className="text-team-b">B</span>
      </span>
      <span className="whitespace-nowrap text-ink-muted">set {score.set_no}: {score.a}–{score.b}</span>
      {score.demo && <span className="whitespace-nowrap text-ink-muted">(demo data)</span>}
    </span>
  )
}

export function VideoRow({ video }: { video: Video }) {
  const status = video.job?.status
  const duration = video.frames && video.fps ? formatDuration(video.frames / video.fps) : '–'
  return (
    <tr className="border-b border-line align-middle last:border-b-0 hover:bg-panel">
      <td className="py-2.5 pr-4 pl-4">
        <Link to={`/videos/${video.id}`} className="font-mono text-[13px] hover:underline">
          <BreakableName name={video.name} />
        </Link>
        <div className="font-mono text-[12px] text-ink-muted sm:hidden">{duration}</div>
      </td>
      <td className="hidden py-2.5 pr-4 font-mono text-[12px] text-ink-muted sm:table-cell">{duration}</td>
      <td className="py-2.5 pr-4">
        {status === 'queued' || status === 'running' ? (
          <Progress video={video} />
        ) : status === 'failed' ? (
          <Failed video={video} />
        ) : video.score ? (
          <Score score={video.score} />
        ) : (
          <span className="text-ink-muted">No rallies yet</span>
        )}
      </td>
    </tr>
  )
}
