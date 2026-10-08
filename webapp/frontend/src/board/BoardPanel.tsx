import { lazy, Suspense, useState } from 'react'
import { useFlights, usePlayers } from '../api/queries'
import type { Rally, StageInfo } from '../api/types'
import { TacticsBoard2D } from './TacticsBoard2D'

const TacticsBoard3D = lazy(() => import('./TacticsBoard3D'))

type View = '2d' | '3d'

/** Tactics board for the rally at the playhead: top-down (2D) or rotatable (3D). */
export function BoardPanel({ videoId, rally, trajectory }: { videoId: string; rally?: Rally; trajectory?: StageInfo }) {
  const [view, setView] = useState<View>('2d')
  const start = rally?.start_s ?? 0
  const end = rally?.end_s ?? 0
  const flights = useFlights(videoId, start, end, rally !== undefined)
  const players = usePlayers(videoId, start, end, rally !== undefined)

  if (!rally) return <p className="py-2 text-ink-muted">Move the playhead into a rally to see its flights.</p>
  if (flights.isPending) return <p className="py-2 text-ink-muted">Loading…</p>
  if (flights.isError) {
    return <p className="py-2 text-ink-muted">3D flights appear after the analysis reaches “Reconstructing 3D flights”.</p>
  }
  const list = flights.data
  if (list.length === 0) {
    return <p className="py-2 text-ink-muted">{trajectory?.message ?? 'No ball flights were reconstructed in this rally.'}</p>
  }
  const demo = list.some((f) => f.source === 'demo')
  const toggle = (v: View) =>
    `rounded px-2 py-0.5 font-medium ${view === v ? 'bg-panel text-ink shadow-[inset_0_0_0_1px_var(--line)]' : 'text-ink-muted hover:text-ink'}`

  return (
    <figure className="space-y-2 text-[13px]">
      <div className="flex items-center justify-between gap-2">
        <div role="group" aria-label="Board view" className="flex gap-1">
          <button type="button" className={toggle('2d')} aria-pressed={view === '2d'} onClick={() => setView('2d')}>2D</button>
          <button type="button" className={toggle('3d')} aria-pressed={view === '3d'} onClick={() => setView('3d')}>3D</button>
        </div>
        <span className="text-ink-muted">Rally {rally.idx + 1}, {list.length} flight{list.length === 1 ? '' : 's'}</span>
      </div>
      {demo && <p className="text-[12px] text-review">Demo flights: placeholders built from the demo rallies, not measured.</p>}
      {view === '2d' ? (
        <TacticsBoard2D flights={list} players={players.data} />
      ) : (
        <Suspense fallback={<p className="py-6 text-center text-ink-muted">Loading 3D view…</p>}>
          <TacticsBoard3D flights={list} />
        </Suspense>
      )}
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-muted">
        <span>
          <span className="mr-1 inline-block h-2 w-8 rounded-sm align-middle" style={{ background: 'linear-gradient(to right, color-mix(in oklab, var(--accent) 25%, var(--court)), var(--accent))' }} />
          height, low to high
        </span>
        <span>- - - low quality</span>
        <span>· · · not seen by the camera</span>
        <span>● landed in · × out</span>
      </figcaption>
    </figure>
  )
}
