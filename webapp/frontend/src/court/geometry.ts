// Court geometry in metres, matching vball.court: x along the 18 m length (net at x = 9),
// y across the 9 m width.
export const LENGTH = 18
export const WIDTH = 9
export const NET_X = 9
export const ATTACK_OFFSET = 3

export const LINES: [number, number, number, number][] = [
  [0, 0, LENGTH, 0],
  [0, WIDTH, LENGTH, WIDTH],
  [0, 0, 0, WIDTH],
  [LENGTH, 0, LENGTH, WIDTH],
  [NET_X - ATTACK_OFFSET, 0, NET_X - ATTACK_OFFSET, WIDTH],
  [NET_X + ATTACK_OFFSET, 0, NET_X + ATTACK_OFFSET, WIDTH],
]

/** Same rule as vball.court.is_in: the lines are part of the court. */
export function isIn(x: number, y: number): boolean {
  return x >= 0 && x <= LENGTH && y >= 0 && y <= WIDTH
}
