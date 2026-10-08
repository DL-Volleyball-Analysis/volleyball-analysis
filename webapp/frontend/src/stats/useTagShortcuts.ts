import { useEffect } from 'react'
import type { TagKind } from '../api/types'
import type { Clock } from '../playback/clock'

function typing(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
}

/** T starts an attack tag, S a serve tag, at the exact playback time; playback pauses. */
export function useTagShortcuts({ clock, onStart }: { clock: Clock; onStart: (kind: TagKind, timeS: number) => void }) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return
      const key = e.key.toLowerCase()
      if (key !== 't' && key !== 's') return
      e.preventDefault() // the key must not land in the entry field that opens next
      clock.pause()
      onStart(key === 't' ? 'attack' : 'serve', clock.exactTime())
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [clock, onStart])
}
