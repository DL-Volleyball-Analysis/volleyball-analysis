import { useEffect, useRef } from 'react'
import type { Flight, PlayerWindow } from '../api/types'
import { LENGTH, LINES, NET_X, WIDTH, isIn } from '../court/geometry'
import { useClock, usePlaybackTime } from '../playback/clock'
import { apex, ballAt, flightLabel, heightShare, segments } from './flightGeometry'

const MARGIN = 2.5 // metres of free zone drawn around the court
const HAIR = { vectorEffect: 'non-scaling-stroke' as const }

function colour(z: number) {
  return `color-mix(in oklab, var(--accent) ${heightShare(z)}%, var(--court))`
}

function FlightPath({ f, i }: { f: Flight; i: number }) {
  const label = flightLabel(f, i)
  const low = f.quality === 'low'
  const top = apex(f)
  return (
    <g tabIndex={0} role="img" aria-label={label} className="outline-none focus-visible:[&>path]:opacity-100" data-testid="flight">
      <title>{label}</title>
      {segments(f).map(({ a, b }, k) => (
        <path
          key={k}
          d={`M${a.x},${a.y}L${b.x},${b.y}`}
          stroke={colour((a.z + b.z) / 2)}
          strokeWidth={b.observed ? 2.5 : 1.5}
          strokeDasharray={low ? '4 3' : b.observed ? undefined : '1 3'}
          strokeLinecap="round"
          {...HAIR}
          data-observed={b.observed}
        />
      ))}
      {top && (
        <text x={top.x} y={top.y - 0.35} fontSize={0.42} textAnchor="middle" fill="var(--ink-muted)">{f.apex_m!.toFixed(1)} m</text>
      )}
      {f.net_crossing && (
        <text x={NET_X + 0.15} y={f.net_crossing.y_m - 0.25} fontSize={0.42} fill="var(--ink)" data-testid="net-height">
          {f.net_crossing.height_m.toFixed(1)} m
        </text>
      )}
      {f.landing && <LandingMark x={f.landing.x_m} y={f.landing.y_m} />}
      {f.samples.length > 0 && f.anchors.map((end) => {
        const s = end === 'start' ? f.samples[0] : f.samples[f.samples.length - 1]
        return <AnchorMark key={end} x={s.x} y={s.y} />
      })}
    </g>
  )
}

/** A touch the 3D fit tied to a player's court position (change constrain-3d-flights). */
function AnchorMark({ x, y }: { x: number; y: number }) {
  const r = 0.32
  return <path d={`M${x},${y - r}L${x + r},${y}L${x},${y + r}L${x - r},${y}Z`} fill="none" stroke="var(--ink)" strokeWidth={1.5} {...HAIR} data-testid="anchor" />
}

function LandingMark({ x, y }: { x: number; y: number }) {
  const r = 0.26
  return isIn(x, y) ? (
    <circle cx={x} cy={y} r={r} fill="var(--ink)" data-testid="landing-in" />
  ) : (
    <path d={`M${x - r},${y - r}L${x + r},${y + r}M${x + r},${y - r}L${x - r},${y + r}`} stroke="var(--ink)" strokeWidth={2} {...HAIR} data-testid="landing-out" />
  )
}

/**
 * Top-down court with the rally's flights: ground tracks from the 3D paths, height as the depth of one
 * hue plus labels (apex, net crossing), landing marks, dashed low-quality flights, thin dotted frames the
 * camera did not see, and players when known. The ball marker moves in an animation frame from the
 * video's own time, outside React.
 */
export function TacticsBoard2D({ flights, players }: { flights: readonly Flight[]; players?: PlayerWindow }) {
  const clock = useClock()
  const ball = useRef<SVGCircleElement>(null)
  const heightLabel = useRef<SVGTextElement>(null)
  const flightsRef = useRef(flights)
  useEffect(() => {
    flightsRef.current = flights
  })

  useEffect(() => {
    let frame = 0
    const move = () => {
      frame = requestAnimationFrame(move)
      const p = ballAt(flightsRef.current, clock.exactTime())
      if (!ball.current || !heightLabel.current) return
      ball.current.style.display = p ? '' : 'none'
      heightLabel.current.style.display = p ? '' : 'none'
      if (!p) return
      ball.current.setAttribute('cx', String(p.x))
      ball.current.setAttribute('cy', String(p.y))
      heightLabel.current.setAttribute('x', String(p.x + 0.4))
      heightLabel.current.setAttribute('y', String(p.y - 0.4))
      heightLabel.current.textContent = `${p.z.toFixed(1)} m`
    }
    frame = requestAnimationFrame(move)
    return () => cancelAnimationFrame(frame)
  }, [clock])

  // players at the playback time (5 updates per second at most; see playback/clock.ts)
  const t = usePlaybackTime()
  const frameNow = players ? Math.round(t * players.fps) : -1
  const people = players?.placed ? players.boxes.filter((b) => b.frame === frameNow && b.court_x != null && b.role !== 'other') : []

  return (
    <svg
      viewBox={`${-MARGIN} ${-MARGIN} ${LENGTH + 2 * MARGIN} ${WIDTH + 2 * MARGIN}`}
      className="w-full"
      role="group"
      aria-label={`Tactics board with ${flights.length} flights`}
    >
      <rect x={-MARGIN} y={-MARGIN} width={LENGTH + 2 * MARGIN} height={WIDTH + 2 * MARGIN} fill="var(--free-zone)" />
      <rect x={0} y={0} width={LENGTH} height={WIDTH} fill="var(--court)" />
      {LINES.map(([x1, y1, x2, y2]) => (
        <line key={`${x1}-${y1}-${x2}-${y2}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--court-line)" strokeWidth={1} {...HAIR} />
      ))}
      <line x1={NET_X} y1={-0.5} x2={NET_X} y2={WIDTH + 0.5} stroke="var(--court-line)" strokeWidth={2} {...HAIR} />
      {people.map((p) => (
        <circle key={p.track_id} cx={p.court_x!} cy={p.court_y!} r={0.3} fill="none" stroke="var(--ink-muted)" strokeWidth={1.5} {...HAIR} data-testid="player" />
      ))}
      {flights.map((f, i) => <FlightPath key={`${f.start_s}`} f={f} i={i} />)}
      <circle ref={ball} r={0.22} fill="#ffd23f" stroke="#000" strokeWidth={1} {...HAIR} style={{ display: 'none' }} data-testid="ball-marker" />
      <text ref={heightLabel} fontSize={0.45} fill="var(--ink)" style={{ display: 'none' }} aria-hidden data-testid="ball-height" />
    </svg>
  )
}
