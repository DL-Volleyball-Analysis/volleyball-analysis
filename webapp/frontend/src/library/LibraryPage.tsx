import { useJobStream } from '../api/jobStream'
import { useVideos } from '../api/queries'
import type { Video } from '../api/types'
import { UploadDrop } from './UploadDrop'
import { VideoRow } from './VideoRow'

/** Subscribes to live progress for one video; renders nothing. */
function FollowJob({ video }: { video: Video }) {
  useJobStream(video)
  return null
}

export function LibraryPage() {
  const videos = useVideos()
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <h1 className="text-[28px] leading-tight font-semibold tracking-tight">Matches</h1>
      <div className="mt-4">
        <UploadDrop />
      </div>
      {videos.isPending ? (
        <p className="mt-6 text-ink-muted">Loading matches…</p>
      ) : videos.isError ? (
        <p className="mt-6 text-review">Could not reach the analysis server: {videos.error.message}</p>
      ) : videos.data.length === 0 ? (
        <p className="mt-6 text-ink-muted">No matches yet. Add a video above to start the analysis.</p>
      ) : (
        <div className="mt-5 overflow-x-auto rounded-[10px] border border-line bg-window shadow-[var(--shadow-window)]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-line bg-panel text-[12px] text-ink-muted">
                <th className="py-2 pr-4 pl-4 font-medium">Match</th>
                <th className="hidden py-2 pr-4 font-medium sm:table-cell">Length</th>
                <th className="py-2 pr-4 font-medium">Result</th>
              </tr>
            </thead>
            <tbody>
              {videos.data.map((v) => (
                <VideoRow key={v.id} video={v} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {videos.data?.map((v) => <FollowJob key={v.id} video={v} />)}
    </div>
  )
}
