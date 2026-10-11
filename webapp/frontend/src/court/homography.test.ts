import { describe, expect, it } from 'vitest'
import { COURT_CORNERS, PRESETS, apply, cornersAt, cornersFrom, courtSegments, homography, plausible, type CourtShot, type Pt } from './homography'

const CORNERS: Pt[] = [[600, 300], [1320, 300], [1700, 800], [220, 800]]

describe('homography', () => {
  it('maps the court corners onto the image corners and keeps the net in the middle', () => {
    const h = homography(COURT_CORNERS, CORNERS)!
    COURT_CORNERS.forEach((c, i) => {
      const [x, y] = apply(h, c)
      expect(x).toBeCloseTo(CORNERS[i][0], 6)
      expect(y).toBeCloseTo(CORNERS[i][1], 6)
    })
    const [nx] = apply(h, [9, 4.5])
    expect(nx).toBeCloseTo(960, 6) // symmetric trapezoid: the centre of the court is on the image axis
  })

  it('is null for degenerate corners', () => {
    expect(homography(COURT_CORNERS, [[0, 0], [0, 0], [0, 0], [0, 0]])).toBeNull()
  })

  it('draws seven court lines', () => {
    const segs = courtSegments(CORNERS)
    expect(segs).toHaveLength(7)
    expect(segs[0][0][0]).toBeCloseTo(220, 6) // near sideline starts at the near left corner
  })
})

describe('cornersAt', () => {
  const shots: CourtShot[] = [
    { start_frame: 0, end_frame: 49, status: 'ok', samples: [
      { frame: 0, corners_px: [[0, 0], [10, 0], [10, 10], [0, 10]] },
      { frame: 10, corners_px: [[10, 0], [20, 0], [20, 10], [10, 10]] },
    ] },
    { start_frame: 50, end_frame: 99, status: 'needs_review', samples: [{ frame: 60, corners_px: [[0, 0], [1, 0], [1, 1], [0, 1]] }] },
  ]
  it('interpolates between samples and holds at the ends', () => {
    expect(cornersAt(shots, 5)![0]).toEqual([5, 0])
    expect(cornersAt(shots, 30)![0]).toEqual([10, 0])
  })
  it('never returns a doubtful court or a frame outside the shots', () => {
    expect(cornersAt(shots, 60)).toBeNull()
    expect(cornersAt(shots, 120)).toBeNull()
  })
})

describe('plausible', () => {
  it('accepts a court and rejects crossed or tiny ones', () => {
    expect(plausible(CORNERS, 1920, 1080)).toBe(true)
    expect(plausible([CORNERS[0], CORNERS[2], CORNERS[1], CORNERS[3]], 1920, 1080)).toBe(false)
    expect(plausible([[0, 0], [10, 0], [10, 10], [0, 10]], 1920, 1080)).toBe(false)
  })
})

describe('cornersFrom', () => {
  it('recovers the court corners from the near half', () => {
    const h = homography(COURT_CORNERS, CORNERS)!
    const near = PRESETS.near_half.court.map((c) => apply(h, c))
    cornersFrom(near, PRESETS.near_half.court)!.forEach(([x, y], i) => {
      expect(x).toBeCloseTo(CORNERS[i][0], 6)
      expect(y).toBeCloseTo(CORNERS[i][1], 6)
    })
  })
})
