import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import { rallies } from '../test/fixtures'
import { formatTimecode } from '../ui/format'
import { RallyInspector } from './RallyInspector'

const row = (label: string) => screen.getByText(label).closest('div')!

describe('RallyInspector', () => {
  test('shows the rally properties', () => {
    const list = rallies(['a', 'b'])
    list[1] = { ...list[1], start_s: 4.41, end_s: 6, confidence: 0.42, landing_x: 19.2, landing_y: 3, winner_override: 'a', effective_winner: 'a' }
    render(<RallyInspector rallies={list} index={1} onCorrect={() => {}} />)
    expect(row('Rally')).toHaveTextContent('2 of 2')
    expect(row('Time')).toHaveTextContent('0:04.4 – 0:06.0')
    expect(row('Winner')).toHaveTextContent('Aedited, model said B')
    expect(row('Confidence')).toHaveTextContent('42%') // corrected by the user: no longer flagged
    expect(row('Confidence')).not.toHaveTextContent('check')
    expect(row('Landing')).toHaveTextContent('x 19.2 m, y 3.0 mout')
  })

  test('flags a low-confidence rally the user has not corrected', () => {
    const list = rallies(['b'], { confidence: 0.42 })
    render(<RallyInspector rallies={list} index={0} onCorrect={() => {}} />)
    expect(row('Confidence')).toHaveTextContent('42% ▲ check this rally')
  })

  test('buttons correct the winner; Clear only when corrected', async () => {
    const onCorrect = vi.fn()
    render(<RallyInspector rallies={rallies(['a'])} index={0} onCorrect={onCorrect} />)
    const actions = screen.getByText('Set winner').parentElement!
    expect(within(actions).getByRole('button', { name: 'Clear' })).toBeDisabled()
    await userEvent.click(within(actions).getByRole('button', { name: 'B' }))
    expect(onCorrect).toHaveBeenCalledWith(0, 'b')
  })

  test('before the first rally', () => {
    render(<RallyInspector rallies={rallies(['a'])} index={-1} onCorrect={() => {}} />)
    expect(screen.getByText('Before the first rally.')).toBeInTheDocument()
  })
})

test('timecodes keep tenths', () => {
  expect([formatTimecode(4.41), formatTimecode(65.06), formatTimecode(0)]).toEqual(['0:04.4', '1:05.1', '0:00.0'])
})
