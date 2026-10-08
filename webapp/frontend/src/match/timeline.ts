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
