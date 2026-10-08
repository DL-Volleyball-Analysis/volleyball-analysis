// TanStack Query hooks. Everything about one video lives under ['video', id], so invalidating
// that prefix refreshes its stages, rallies and ball data together.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Rally, StageName, Team } from './types'

export const BALL_WINDOW_S = 30

export const keys = {
  videos: ['videos'] as const,
  video: (id: string) => ['video', id] as const,
  stages: (id: string) => ['video', id, 'stages'] as const,
  rallies: (id: string) => ['video', id, 'rallies'] as const,
  ball: (id: string, window: number) => ['video', id, 'ball', window] as const,
  coverage: (id: string, bins: number) => ['video', id, 'coverage', bins] as const,
}

/** Ball data is fetched in fixed windows so a long match is never loaded at once. */
export function ballWindow(timeS: number): number {
  return Math.max(0, Math.floor(timeS / BALL_WINDOW_S))
}

export const useVideos = () => useQuery({ queryKey: keys.videos, queryFn: api.videos })

export const useVideo = (id: string) => useQuery({ queryKey: keys.video(id), queryFn: () => api.video(id) })

export const useStages = (id: string) => useQuery({ queryKey: keys.stages(id), queryFn: () => api.stages(id) })

export const useRallies = (id: string) =>
  useQuery({ queryKey: keys.rallies(id), queryFn: () => api.rallies(id) })

export const useBallWindow = (id: string, window: number, enabled = true) =>
  useQuery({
    queryKey: keys.ball(id, window),
    queryFn: () => api.ball(id, window * BALL_WINDOW_S, (window + 1) * BALL_WINDOW_S),
    enabled,
    staleTime: Infinity, // ball tracks only change when the analysis reruns, which invalidates them
    retry: false, // 404 until ball tracking has run
  })

export const COVERAGE_BINS = 400

/** Ball detection coverage over the whole video, for the timeline's ball lane (404 until tracked). */
export const useBallCoverage = (id: string) =>
  useQuery({ queryKey: keys.coverage(id, COVERAGE_BINS), queryFn: () => api.ballCoverage(id, COVERAGE_BINS), retry: false })

export function useUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.upload,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.videos }),
  })
}

export function useStartJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, fromStage }: { id: string; fromStage?: StageName }) => api.startJob(id, fromStage),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: keys.videos })
      qc.invalidateQueries({ queryKey: keys.video(id) })
    },
  })
}

/** Optimistic: the rally shows the new winner at once; the server's recomputed list replaces it. */
export function useCorrectRally(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ idx, winner }: { idx: number; winner: Team | null }) => api.correctRally(id, idx, winner),
    onMutate: async ({ idx, winner }) => {
      await qc.cancelQueries({ queryKey: keys.rallies(id) })
      const previous = qc.getQueryData<Rally[]>(keys.rallies(id))
      qc.setQueryData<Rally[]>(keys.rallies(id), (list) =>
        list?.map((r) => (r.idx === idx ? { ...r, winner_override: winner, effective_winner: winner ?? r.winner } : r)),
      )
      return { previous }
    },
    onError: (_err, _vars, context) => qc.setQueryData(keys.rallies(id), context?.previous),
    onSuccess: (rallies) => {
      qc.setQueryData(keys.rallies(id), rallies)
      qc.invalidateQueries({ queryKey: keys.videos })
    },
  })
}
