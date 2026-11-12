import type { ActionEvent } from '../api/types'

export const CLIP_LEAD_S = 1.5 // a played clip starts this long before the action
export const CLIP_TAIL_S = 2.0 // and ends this long after it

/** Who did an action, as shown in the list and offered in the player filter. */
export const playerOf = (a: ActionEvent) =>
  a.number != null ? `#${a.number}` : a.track_id != null ? `ID ${a.track_id}` : '–'
export const playerKey = (a: ActionEvent) => `${a.team ?? '-'} ${playerOf(a)}`

/**
 * Where a playing list goes at video time t, playing the action at `index`: the same action, the next one (highlighted
 * once playback reaches it; `seek` only when its clip starts after t, so overlapping clips play through instead of
 * jumping back), or null after the last clip.
 */
export function advance(list: readonly ActionEvent[], index: number, t: number): { at: number; seek: boolean } | null {
  const next = index + 1
  if (t >= list[index].start_s + CLIP_TAIL_S) {
    if (next >= list.length) return null
    return { at: next, seek: list[next].start_s - CLIP_LEAD_S > t }
  }
  if (next < list.length && list[next].start_s <= t) return { at: next, seek: false }
  return { at: index, seek: false }
}
