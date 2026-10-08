import { describe, expect, test } from 'vitest'
import { rallies } from '../test/fixtures'
import { rallyAt } from './useRallyAt'

// fixture rallies: start at idx * 10 s, last 6 s
const r = rallies(['a', 'b', 'a'])

describe('rallyAt', () => {
  test('before the first rally', () => {
    expect(rallyAt(r, -1)).toEqual({ index: -1, inRally: false })
  })
  test('inside a rally, including both ends', () => {
    expect(rallyAt(r, 0)).toEqual({ index: 0, inRally: true })
    expect(rallyAt(r, 13)).toEqual({ index: 1, inRally: true })
    expect(rallyAt(r, 16)).toEqual({ index: 1, inRally: true })
  })
  test('in the gap between rallies: the last finished rally', () => {
    expect(rallyAt(r, 17)).toEqual({ index: 1, inRally: false })
  })
  test('after the last rally', () => {
    expect(rallyAt(r, 99)).toEqual({ index: 2, inRally: false })
  })
  test('no rallies', () => {
    expect(rallyAt([], 5)).toEqual({ index: -1, inRally: false })
  })
})
