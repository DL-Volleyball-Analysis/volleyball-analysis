import type { Rally } from '../api/types'
import { LENGTH, LINES, NET_X, WIDTH, isIn } from './geometry'

const MARGIN = 2.5 // metres of free zone drawn around the court
// Lines are drawn 1 px wide at any size (non-scaling stroke), like a technical drawing.
const HAIR = { vectorEffect: 'non-scaling-stroke' as const, strokeWidth: 1 }

function Marker({ rally, current }: { rally: Rally; current: boolean }) {
  const x = rally.landing_x!
  const y = rally.landing_y!
  const team = rally.effective_winner
  const tone = team === 'a' ? 'var(--team-a)' : team === 'b' ? 'var(--team-b)' : 'var(--ink-muted)'
  const r = 0.26
  const label = `Rally ${rally.idx + 1}: ${isIn(x, y) ? 'in' : 'out'}${team ? `, won by ${team.toUpperCase()}` : ''}`
  return (
    <g opacity={current ? 1 : 0.45} aria-label={label} role="img">
      <title>{label}</title>
      {isIn(x, y) ? (
        <circle cx={x} cy={y} r={r} fill={tone} />
      ) : (
        <path d={`M${x - r},${y - r}L${x + r},${y + r}M${x + r},${y - r}L${x - r},${y + r}`} stroke={tone} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      )}
      {current && <circle cx={x} cy={y} r={r + 0.22} fill="none" stroke="var(--accent)" {...HAIR} strokeWidth={1.5} />}
      {team && (
        <text x={x + r + 0.18} y={y + 0.16} fontSize={0.48} fontWeight={600} fill={tone}>
          {team.toUpperCase()}
        </text>
      )}
    </g>
  )
}

/** The court to scale with each rally's landing point; the current rally is highlighted. */
export function CourtMap({ rallies, currentIndex }: { rallies: readonly Rally[]; currentIndex: number }) {
  const landed = rallies.filter((r) => r.landing_x != null && r.landing_y != null)
  const current = rallies[currentIndex]
  return (
    <figure>
      <svg
        viewBox={`${-MARGIN} ${-MARGIN} ${LENGTH + 2 * MARGIN} ${WIDTH + 2 * MARGIN}`}
        className="w-full"
        role="group"
        aria-label={`Court map with ${landed.length} landing points`}
      >
        <rect x={-MARGIN} y={-MARGIN} width={LENGTH + 2 * MARGIN} height={WIDTH + 2 * MARGIN} fill="var(--free-zone)" />
        <rect x={0} y={0} width={LENGTH} height={WIDTH} fill="var(--court)" />
        {LINES.map(([x1, y1, x2, y2]) => (
          <line key={`${x1}-${y1}-${x2}-${y2}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--court-line)" {...HAIR} />
        ))}
        <line x1={NET_X} y1={-0.5} x2={NET_X} y2={WIDTH + 0.5} stroke="var(--court-line)" {...HAIR} strokeWidth={2} />
        {landed.filter((r) => r !== current).map((r) => <Marker key={r.idx} rally={r} current={false} />)}
        {current && current.landing_x != null && <Marker rally={current} current />}
      </svg>
      <figcaption className="mt-1.5 flex gap-4 text-[13px] text-ink-muted">
        <span>● landed in</span>
        <span>× out</span>
        <span>net at centre</span>
      </figcaption>
    </figure>
  )
}
