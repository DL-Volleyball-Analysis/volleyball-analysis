import { useMemo } from 'react'
import type { Rally } from '../api/types'
import { usePlaybackTime } from './clock'

export type RallyPosition = {
  /** Rally playing at time t, or the last rally finished before t; -1 before the first rally. */
  index: number
  /** True when t is inside that rally, false in the gap after it. */
  inRally: boolean
}

/** Rallies are sorted by start time (the backend orders them by idx). Binary search. */
export function rallyAt(rallies: readonly Rally[], t: number): RallyPosition {
  let lo = 0
  let hi = rallies.length - 1
  let last = -1 // last rally starting at or before t
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (rallies[mid].start_s <= t) {
      last = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  if (last < 0) return { index: -1, inRally: false }
  return { index: last, inRally: t <= rallies[last].end_s }
}

export function useRallyAt(rallies: readonly Rally[] | undefined): RallyPosition {
  const t = usePlaybackTime()
  return useMemo(() => rallyAt(rallies ?? [], t), [rallies, t])
}
