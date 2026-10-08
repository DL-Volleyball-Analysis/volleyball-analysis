import css from './theme.css?raw'
import { describe, expect, test } from 'vitest'

// WCAG 2.x contrast: 4.5 for normal text, 3 for UI marks and graphics
const [lightBlock, darkBlock] = css.split(':root[data-theme="dark"]')

function tokens(block: string): Record<string, string> {
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})/gi)].map((m) => [m[1], m[2]]))
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

const TEXT: [string, string][] = [
  ['ink', 'window'], ['ink', 'bg'], ['ink', 'panel'],
  ['ink-muted', 'window'], ['ink-muted', 'bg'], ['ink-muted', 'panel'],
  ['team-a', 'window'], ['team-b', 'window'], ['team-a', 'panel'], ['team-b', 'panel'],
  ['accent', 'window'], ['accent', 'bg'], ['on-accent', 'accent'],
  ['review', 'window'], ['review', 'bg'], ['review', 'panel'],
]
const MARKS: [string, string][] = [
  ['mute', 'window'], ['accent', 'panel'], ['lane-ball', 'window'], ['lane-landing', 'window'],
  ['team-a', 'court'], ['team-b', 'court'], ['court-line', 'court'], ['court-line', 'free-zone'],
]

describe.each([['light', tokens(lightBlock)], ['dark', tokens(darkBlock)]])('%s theme', (_, t) => {
  test.each(TEXT)('text %s on %s ≥ 4.5', (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(4.5)
  })
  test.each(MARKS)('mark %s on %s ≥ 3', (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(3)
  })
})
