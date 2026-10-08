import type { StageName } from '../api/types'

/** 83.4 -> "1:23"; 3725 -> "1:02:05" */
export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`
}

/** 4.41 -> "0:04.4": timecode with tenths, for the inspector. */
export function formatTimecode(seconds: number): string {
  const t = Math.max(0, seconds)
  const m = Math.floor(t / 60)
  const s = (t - m * 60).toFixed(1).padStart(4, '0')
  return `${m}:${s}`
}

/** What each analysis stage does, in the user's words. */
export const STAGE_LABEL: Record<StageName, string> = {
  decode: 'Reading the video',
  court: 'Finding the court',
  ball: 'Tracking the ball',
  events: 'Finding contacts and landings',
  rallies: 'Scoring rallies',
}
