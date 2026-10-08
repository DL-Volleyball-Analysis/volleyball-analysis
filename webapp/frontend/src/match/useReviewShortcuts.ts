import { useEffect } from 'react'
import type { Rally, Team } from '../api/types'
import type { Clock } from '../playback/clock'

/** Elements that keep their own keys: typing fields, and controls where Space/Enter activate them. */
function ownsKeys(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  return ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A', 'VIDEO'].includes(target.tagName)
}

/**
 * J / K previous / next rally, Space play / pause, 1 / 2 set the current rally's winner to A / B,
 * 0 clear the correction. `index` is the rally at the playback position (see rallyAt).
 */
export function useReviewShortcuts({ rallies, index, clock, correct }: {
  rallies: readonly Rally[]
  index: number
  clock: Clock
  correct: (idx: number, winner: Team | null) => void
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const typing = e.target instanceof HTMLElement && (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable)
      if (typing) return
      const current = rallies[index]
      switch (e.key) {
        case 'j':
        case 'J':
          if (index > 0) clock.seek(rallies[index - 1].start_s)
          break
        case 'k':
        case 'K':
          if (index + 1 < rallies.length) clock.seek(rallies[index + 1].start_s)
          break
        case ' ':
          if (ownsKeys(e.target)) return
          e.preventDefault()
          clock.togglePlay()
          break
        case '1':
        case '2':
        case '0':
          if (current) correct(current.idx, e.key === '1' ? 'a' : e.key === '2' ? 'b' : null)
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [rallies, index, clock, correct])
}
