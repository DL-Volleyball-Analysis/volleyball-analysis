import type { Job, Rally, Video } from '../api/types'

export const job = (patch: Partial<Job> = {}): Job => ({
  id: 'j1', video_id: 'v1', status: 'done', from_stage: 'decode', stage: null, progress: 1, error: null,
  created_at: '2026-10-08T00:00:00Z', updated_at: '2026-10-08T00:00:00Z', ...patch,
})

export const video = (patch: Partial<Video> = {}): Video => ({
  id: 'v1', name: 'final_set3', fps: 25, frames: 2500, width: 1920, height: 1080,
  created_at: '2026-10-08T00:00:00Z', job: job(), score: null, ...patch,
})

/** Rallies back to back, 10 s apart and 6 s long, with scores as the backend computes them. */
export function rallies(winners: ('a' | 'b' | null)[], patch: Partial<Rally> = {}): Rally[] {
  let a = 0, b = 0
  return winners.map((w, idx) => {
    if (w === 'a') a++
    if (w === 'b') b++
    return {
      idx, start_s: idx * 10, end_s: idx * 10 + 6, winner: w, winner_override: null, effective_winner: w,
      reason: 'in', confidence: 0.9, landing_x: 4, landing_y: 4, source: 'model',
      score: { set_no: 1, a, b, sets_a: 0, sets_b: 0, set_over: false }, ...patch,
    }
  })
}
