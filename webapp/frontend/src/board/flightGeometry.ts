import type { Flight, FlightSample } from '../api/types'

export const NET_TOP_M = 2.43
const MAX_HEIGHT_M = 5 // top of the height colour scale

/** Ball position at time t (seconds), interpolated between a flight's samples; null between flights. */
export function ballAt(flights: readonly Flight[], t: number): FlightSample | null {
  for (const f of flights) {
    if (t < f.start_s || t > f.end_s || f.samples.length === 0) continue
    const s = f.samples
    let i = 0
    while (i + 1 < s.length && s[i + 1].t <= t) i++
    const a = s[i], b = s[Math.min(i + 1, s.length - 1)]
    const k = b.t > a.t ? (t - a.t) / (b.t - a.t) : 0
    return { t, x: a.x + k * (b.x - a.x), y: a.y + k * (b.y - a.y), z: a.z + k * (b.z - a.z), observed: a.observed }
  }
  return null
}

/** Height as a share (0-100) of one hue: low = light, high = strong. Paired with height labels. */
export function heightShare(z: number): number {
  return Math.round(25 + 75 * Math.min(Math.max(z, 0), MAX_HEIGHT_M) / MAX_HEIGHT_M)
}

/** Consecutive sample pairs, for drawing segments coloured by height and styled by observation. */
export function segments(f: Flight): { a: FlightSample; b: FlightSample }[] {
  return f.samples.slice(1).map((b, i) => ({ a: f.samples[i], b }))
}

/** Where the flight peaks, when it rises before falling. */
export function apex(f: Flight): FlightSample | null {
  if (f.apex_m == null || f.samples.length === 0) return null
  return f.samples.reduce((m, s) => (s.z > m.z ? s : m), f.samples[0])
}

export function flightLabel(f: Flight, i: number): string {
  const parts = [`Flight ${i + 1}`, `${f.start_speed_mps.toFixed(0)} m/s`]
  if (f.apex_m != null) parts.push(`apex ${f.apex_m.toFixed(1)} m`)
  if (f.net_crossing) parts.push(`crosses the net at ${f.net_crossing.height_m.toFixed(1)} m`)
  if (f.landing) parts.push(`lands at x ${f.landing.x_m.toFixed(1)} m, y ${f.landing.y_m.toFixed(1)} m`)
  if (f.quality === 'low') parts.push(`low quality: ${f.reasons.join(', ')}`)
  return parts.join(', ')
}
