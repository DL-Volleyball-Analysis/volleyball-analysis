// Live job progress: one EventSource per running video writes each job event into the query
// cache, so every view showing that video updates without polling.
import { useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { api } from './client'
import { keys } from './queries'
import type { Job, Video } from './types'

const FINISHED: Job['status'][] = ['done', 'failed']

type EventSourceLike = Pick<EventSource, 'close' | 'onmessage'>

export function followJob(
  qc: QueryClient,
  videoId: string,
  open: (url: string) => EventSourceLike = (url) => new EventSource(url),
): () => void {
  const es = open(api.jobStreamUrl(videoId))
  es.onmessage = (event) => {
    const job = JSON.parse(event.data) as Job | null
    if (job === null) {
      es.close()
      return
    }
    qc.setQueryData<Video>(keys.video(videoId), (v) => v && { ...v, job })
    qc.setQueryData<Video[]>(keys.videos, (list) => list?.map((v) => (v.id === videoId ? { ...v, job } : v)))
    if (FINISHED.includes(job.status)) {
      es.close()
      // results changed: refresh stages, rallies, ball data and the score summary once
      qc.invalidateQueries({ queryKey: keys.video(videoId) })
      qc.invalidateQueries({ queryKey: keys.videos })
    }
  }
  return () => es.close()
}

/** Follow a video's job while it is queued or running. */
export function useJobStream(video: Video | undefined) {
  const qc = useQueryClient()
  const active = video?.job?.status === 'queued' || video?.job?.status === 'running'
  const id = video?.id
  useEffect(() => {
    if (!active || !id) return
    return followJob(qc, id)
  }, [qc, id, active])
}
