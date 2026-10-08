import { QueryClient } from '@tanstack/react-query'
import { describe, expect, test, vi } from 'vitest'
import { followJob } from './jobStream'
import { keys } from './queries'
import type { Job, Video } from './types'

const job = (status: Job['status'], progress: number): Job => ({
  id: 'j1', video_id: 'v1', status, from_stage: 'decode', stage: 'ball', progress, error: null,
  created_at: '', updated_at: '',
})
const video: Video = {
  id: 'v1', name: 'match', fps: 25, frames: 50, width: 320, height: 180, created_at: '', job: job('queued', 0), score: null,
}

function setup() {
  const qc = new QueryClient()
  qc.setQueryData(keys.video('v1'), video)
  qc.setQueryData(keys.videos, [video, { ...video, id: 'v2' }])
  const es = { onmessage: null as EventSource['onmessage'], close: vi.fn(), url: '' }
  const stop = followJob(qc, 'v1', (url) => Object.assign(es, { url }))
  const send = (data: unknown) => es.onmessage!.call(es as never, { data: JSON.stringify(data) } as MessageEvent)
  return { qc, es, stop, send }
}

describe('followJob', () => {
  test('opens the job stream for the video', () => {
    expect(setup().es.url).toBe('/api/videos/v1/jobs/stream')
  })

  test('writes progress into the video and the list', () => {
    const { qc, send, es } = setup()
    send(job('running', 0.4))
    expect(qc.getQueryData<Video>(keys.video('v1'))?.job?.progress).toBe(0.4)
    const list = qc.getQueryData<Video[]>(keys.videos)!
    expect(list[0].job?.progress).toBe(0.4)
    expect(list[1].job?.progress).toBe(0) // other videos untouched
    expect(es.close).not.toHaveBeenCalled()
  })

  test('closes and refreshes the video data when the job finishes', () => {
    const { qc, send, es } = setup()
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    send(job('done', 1))
    expect(es.close).toHaveBeenCalled()
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.video('v1') })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.videos })
  })

  test('cleanup closes the stream', () => {
    const { stop, es } = setup()
    stop()
    expect(es.close).toHaveBeenCalled()
  })
})
