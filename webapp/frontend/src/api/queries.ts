// TanStack Query hooks. Everything about one video lives under ['video', id], so invalidating
// that prefix refreshes its stages, rallies and ball data together.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { Rally, RosterPlayer, StageName, Tag, TagIn, TagPatch, Team } from './types'

export const BALL_WINDOW_S = 30

export const keys = {
  videos: ['videos'] as const,
  video: (id: string) => ['video', id] as const,
  stages: (id: string) => ['video', id, 'stages'] as const,
  rallies: (id: string) => ['video', id, 'rallies'] as const,
  ball: (id: string, window: number) => ['video', id, 'ball', window] as const,
  coverage: (id: string, bins: number) => ['video', id, 'coverage', bins] as const,
  roster: (id: string) => ['video', id, 'roster'] as const,
  tags: (id: string) => ['video', id, 'tags'] as const,
  stats: (id: string) => ['video', id, 'stats'] as const,
  flights: (id: string, start: number, end: number) => ['video', id, 'flights', start, end] as const,
  players: (id: string, start: number, end: number) => ['video', id, 'players', start, end] as const,
  actions: (id: string) => ['video', id, 'actions'] as const,
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
      // tag outcomes and statistics follow the rally winners
      qc.invalidateQueries({ queryKey: keys.tags(id) })
      qc.invalidateQueries({ queryKey: keys.stats(id) })
    },
  })
}

export const useRoster = (id: string) => useQuery({ queryKey: keys.roster(id), queryFn: () => api.roster(id) })
export const useTags = (id: string) => useQuery({ queryKey: keys.tags(id), queryFn: () => api.tags(id) })
export const useStats = (id: string) => useQuery({ queryKey: keys.stats(id), queryFn: () => api.stats(id) })

/** Tag mutations return the full tag list; statistics and the roster (new numbers) are refetched. */
function useTagMutation<V>(id: string, fn: (v: V) => Promise<Tag[]>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (tags) => {
      qc.setQueryData(keys.tags(id), tags)
      qc.invalidateQueries({ queryKey: keys.stats(id) })
      qc.invalidateQueries({ queryKey: keys.roster(id) })
      qc.invalidateQueries({ queryKey: keys.actions(id) }) // a tag can accept a suggestion
    },
  })
}

export const useAddTag = (id: string) => useTagMutation(id, (tag: TagIn) => api.addTag(id, tag))
export const usePatchTag = (id: string) =>
  useTagMutation(id, ({ tagId, patch }: { tagId: string; patch: TagPatch }) => api.patchTag(id, tagId, patch))
export const useDeleteTag = (id: string) => useTagMutation(id, (tagId: string) => api.deleteTag(id, tagId))

export function usePutRoster(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (players: RosterPlayer[]) => api.putRoster(id, players),
    onSuccess: (roster) => {
      qc.setQueryData(keys.roster(id), roster)
      qc.invalidateQueries({ queryKey: keys.stats(id) }) // names
    },
  })
}

/** 3D flights of a time range (a rally); 404 until the trajectory stage has run. */
export const useFlights = (id: string, start: number, end: number, enabled = true) =>
  useQuery({ queryKey: keys.flights(id, start, end), queryFn: () => api.flights(id, start, end), enabled, retry: false })

/** Player boxes and court positions of a time range; 404 until the players stage has run. */
export const usePlayers = (id: string, start: number, end: number, enabled = true) =>
  useQuery({ queryKey: keys.players(id, start, end), queryFn: () => api.players(id, start, end), enabled, retry: false })

/** Action events, shirt numbers and suggested tags; 404 until the actions stage ran (no retry). */
export const useActions = (id: string, enabled = true) =>
  useQuery({ queryKey: keys.actions(id), queryFn: () => api.actions(id), enabled, retry: false })

export function useDismissSuggestion(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sid: string) => api.dismissSuggestion(id, sid),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.actions(id) }),
  })
}
