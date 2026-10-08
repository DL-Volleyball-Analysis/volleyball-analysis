import type { StatLine } from '../api/types'

/** ".200", "-.333", "1.000"; empty ratio (nothing decided) as an en dash, never 0. */
export function ratio(x: number | null | undefined): string {
  if (x == null) return '–'
  const s = x.toFixed(3)
  return s.replace(/^(-?)0\./, '$1.')
}

export function sets(lines: readonly StatLine[]): number[] {
  return [...new Set(lines.map((l) => l.set_no).filter((s): s is number => s != null))].sort((a, b) => a - b)
}
