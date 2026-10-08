import { describe, expect, test } from 'vitest'
import { LENGTH, WIDTH, isIn } from './geometry'

describe('isIn', () => {
  test('lines count as in', () => {
    expect([isIn(0, 0), isIn(LENGTH, WIDTH), isIn(9, 0), isIn(18, 4.5)]).toEqual([true, true, true, true])
  })
  test('just outside any line is out', () => {
    expect([isIn(-0.01, 4), isIn(18.01, 4), isIn(9, -0.01), isIn(9, 9.01)]).toEqual([false, false, false, false])
  })
})
