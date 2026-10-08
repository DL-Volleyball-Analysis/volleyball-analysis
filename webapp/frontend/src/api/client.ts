// Thin fetch wrapper for the backend. In dev, Vite proxies /api to the FastAPI server.
import type {
  BallCoverage, BallWindow, Job, Rally, RosterPlayer, StageInfo, StageName, Stats, Tag, TagIn, TagPatch, Team, Video,
} from './types'

const BASE = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** FastAPI errors carry `detail` as a string, or as a list of validation errors. */
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) return body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
  } catch {
    // not JSON: fall through to the status text
  }
  return res.statusText || `HTTP ${res.status}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init)
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  videos: () => request<Video[]>('/videos'),
  video: (id: string) => request<Video>(`/videos/${id}`),
  stages: (id: string) => request<StageInfo[]>(`/videos/${id}/stages`),
  rallies: (id: string) => request<Rally[]>(`/videos/${id}/rallies`),
  ball: (id: string, start: number, end: number) =>
    request<BallWindow>(`/videos/${id}/ball?start=${start}&end=${end}`),
  ballCoverage: (id: string, bins: number) => request<BallCoverage>(`/videos/${id}/ball/coverage?bins=${bins}`),
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Video>('/videos', { method: 'POST', body })
  },
  startJob: (id: string, fromStage: StageName = 'decode') =>
    request<Job>(`/videos/${id}/jobs`, json('POST', { from_stage: fromStage })),
  correctRally: (id: string, idx: number, winner: Team | null) =>
    request<Rally[]>(`/videos/${id}/rallies/${idx}`, json('PATCH', { winner })),
  deleteVideo: (id: string) => request<void>(`/videos/${id}`, { method: 'DELETE' }),
  roster: (id: string) => request<{ players: RosterPlayer[] }>(`/videos/${id}/roster`),
  putRoster: (id: string, players: RosterPlayer[]) =>
    request<{ players: RosterPlayer[] }>(`/videos/${id}/roster`, json('PUT', { players })),
  tags: (id: string) => request<Tag[]>(`/videos/${id}/tags`),
  addTag: (id: string, tag: TagIn) => request<Tag[]>(`/videos/${id}/tags`, json('POST', tag)),
  patchTag: (id: string, tagId: string, patch: TagPatch) => request<Tag[]>(`/videos/${id}/tags/${tagId}`, json('PATCH', patch)),
  deleteTag: (id: string, tagId: string) => request<Tag[]>(`/videos/${id}/tags/${tagId}`, { method: 'DELETE' }),
  stats: (id: string) => request<Stats>(`/videos/${id}/stats`),
  statsCsvUrl: (id: string) => `${BASE}/videos/${id}/stats?format=csv`,
  fileUrl: (id: string) => `${BASE}/videos/${id}/file`,
  jobStreamUrl: (id: string) => `${BASE}/videos/${id}/jobs/stream`,
}
