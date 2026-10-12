// Court lines on the video: corners interpolated between samples (as vball.court_registration.corners_at) and
// the court -> image homography they define. Pure functions, unit tested.
import { LENGTH, LINES, NET_X, WIDTH } from './geometry'

export type Pt = [number, number]
type CourtSample = { frame: number; corners_px: number[][] }
export type CourtShot = { start_frame: number; end_frame: number; status: string; samples: CourtSample[] }

/** Court corners in the order the backend uses: far left, far right, near right, near left (court metres). */
export const COURT_CORNERS: Pt[] = [[0, WIDTH], [LENGTH, WIDTH], [LENGTH, 0], [0, 0]]

/** Corners (4 image points) at a frame: interpolated between samples, held before the first and after the
 *  last. null outside any shot and in shots that are not ok (a doubtful court is never drawn). */
export function cornersAt(shots: readonly CourtShot[], frame: number): Pt[] | null {
  const shot = shots.find((s) => s.start_frame <= frame && frame <= s.end_frame)
  if (!shot || shot.status !== 'ok' || shot.samples.length === 0) return null
  const ss = shot.samples
  const at = (s: CourtSample) => s.corners_px.map(([x, y]) => [x, y] as Pt)
  if (frame <= ss[0].frame) return at(ss[0])
  if (frame >= ss[ss.length - 1].frame) return at(ss[ss.length - 1])
  const j = ss.findIndex((s) => s.frame >= frame)
  const a = ss[j - 1]
  const b = ss[j]
  const t = (frame - a.frame) / (b.frame - a.frame)
  return a.corners_px.map(([x, y], k) => [x + t * (b.corners_px[k][0] - x), y + t * (b.corners_px[k][1] - y)] as Pt)
}

/** 3 x 3 homography (row-major, h[8] = 1) mapping src[i] -> dst[i] for four point pairs; null if degenerate. */
export function homography(src: readonly Pt[], dst: readonly Pt[]): number[] | null {
  const A: number[][] = []
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i]
    const [u, v] = dst[i]
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y, u])
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y, v])
  }
  // Gauss-Jordan elimination with partial pivoting on the 8 x 9 augmented system
  for (let c = 0; c < 8; c++) {
    let p = c
    for (let r = c + 1; r < 8; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r
    if (Math.abs(A[p][c]) < 1e-12) return null
    ;[A[c], A[p]] = [A[p], A[c]]
    for (let r = 0; r < 8; r++) {
      if (r === c) continue
      const f = A[r][c] / A[c][c]
      for (let k = c; k < 9; k++) A[r][k] -= f * A[c][k]
    }
  }
  return [...A.map((row, i) => row[8] / row[i]), 1]
}

export function apply(h: readonly number[], [x, y]: Pt): Pt {
  const w = h[6] * x + h[7] * y + h[8]
  return [(h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w]
}

/** Four known floor points a user can click (vball.court_registration.CORRECTION_PRESETS), in court metres. */
export const PRESETS = {
  corners: { court: COURT_CORNERS, steps: ['far left corner', 'far right corner', 'near right corner', 'near left corner'] },
  near_half: {
    court: [[9, WIDTH], [9, 0], [0, 0], [0, WIDTH]] as Pt[],
    steps: ['left end of the centre line', 'right end of the centre line', 'right end of the near end line', 'left end of the near end line'],
  },
} as const
export type Preset = keyof typeof PRESETS

/** The four court corners in the image from four known floor points (null if degenerate). */
export function cornersFrom(points: readonly Pt[], court: readonly Pt[] = COURT_CORNERS): Pt[] | null {
  const h = homography(court, points)
  return h ? COURT_CORNERS.map((c) => apply(h, c)) : null
}

/** Court lines (outline, attack lines, centre line) as image segments, from the four image corners. */
export function courtSegments(corners: readonly Pt[]): [Pt, Pt][] {
  const h = homography(COURT_CORNERS, corners)
  if (!h) return []
  const lines: [number, number, number, number][] = [...LINES, [NET_X, 0, NET_X, WIDTH]]
  return lines.map(([x0, y0, x1, y1]) => [apply(h, [x0, y0]), apply(h, [x1, y1])])
}

/** Same rule as vball.court_keypoints.court_is_plausible, in its simplest form: a convex, non-self-crossing
 *  quadrilateral covering at least 2% of the image. Used to warn before saving a correction. */
export function plausible(corners: readonly Pt[], width: number, height: number): boolean {
  if (corners.length !== 4) return false
  let sign = 0
  for (let i = 0; i < 4; i++) {
    const [ax, ay] = corners[i]
    const [bx, by] = corners[(i + 1) % 4]
    const [cx, cy] = corners[(i + 2) % 4]
    const z = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    if (z === 0) return false
    if (sign === 0) sign = Math.sign(z)
    else if (Math.sign(z) !== sign) return false
  }
  let area = 0
  for (let i = 0; i < 4; i++) area += corners[i][0] * corners[(i + 1) % 4][1] - corners[(i + 1) % 4][0] * corners[i][1]
  return Math.abs(area) / 2 >= 0.02 * width * height
}
