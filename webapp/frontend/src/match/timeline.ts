// Pure helpers for the match timeline (unit tested).

const STEPS_S = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800]

/** A ruler step that gives at most `maxLabels` labels over the duration (labels at 0, s, 2s, ...). */
export function rulerStep(duration: number, maxLabels = 10): number {
  return STEPS_S.find((s) => Math.floor(duration / s) + 1 <= maxLabels) ?? STEPS_S[STEPS_S.length - 1]
}

/** Seconds at a horizontal position inside a track of the given box, clamped to the video. */
export function timeAt(clientX: number, box: { left: number; width: number }, duration: number): number {
  if (!box.width) return 0
  return Math.min(duration, Math.max(0, ((clientX - box.left) / box.width) * duration))
}

/**
 * Rows for labels on a lane so they do not overlap: each label takes the first of `rows` rows whose last label is
 * at least `minGap` (a share of the duration) before it; with every row taken it gets null (drawn as a tick, the
 * full description still in its title). Labels are given in time order.
 */
export function labelRows(starts: readonly number[], duration: number, minGap = 0.025, rows = 2): (number | null)[] {
  const gap = minGap * duration
  const last = Array<number>(rows).fill(-Infinity)
  return starts.map((t) => {
    const r = last.findIndex((l) => t - l >= gap)
    if (r < 0) return null
    last[r] = t
    return r
  })
}
