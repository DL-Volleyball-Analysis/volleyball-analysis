import type { Rally } from '../api/types'

/** Score after the rally at the playback position (0-0 before the first rally). */
export function Scoreboard({ rallies, index }: { rallies: readonly Rally[]; index: number }) {
  const s = rallies[index]?.score ?? { set_no: 1, a: 0, b: 0, sets_a: 0, sets_b: 0, set_over: false }
  return (
    <section aria-label="Score" className="flex items-baseline gap-5">
      <span className="text-ink-muted">
        Set <span className="text-ink">{s.set_no}</span>
        {s.set_over && ' ended'}
      </span>
      <span className="text-[24px] leading-none font-semibold">
        <span className="text-team-a">A</span>{' '}
        <span data-testid="points-a">{s.a}</span>
        <span className="px-1.5 text-ink-muted">–</span>
        <span data-testid="points-b">{s.b}</span>{' '}
        <span className="text-team-b">B</span>
      </span>
      <span className="text-ink-muted">
        Sets <span className="text-ink" data-testid="sets">{s.sets_a}–{s.sets_b}</span>
      </span>
    </section>
  )
}
