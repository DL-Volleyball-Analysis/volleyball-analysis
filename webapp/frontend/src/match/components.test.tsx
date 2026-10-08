import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { describe, expect, test, vi } from 'vitest'
import type { Rally } from '../api/types'
import { CourtMap } from '../court/CourtMap'
import { ClockContext, createClock } from '../playback/clock'
import { useRallyAt } from '../playback/useRallyAt'
import { rallies } from '../test/fixtures'
import { LayerMenu } from './LayerMenu'
import { RallyList } from './RallyList'
import { Scoreboard } from './Scoreboard'
import { StagePanel } from './StagePanel'

function BoundScoreboard({ list }: { list: Rally[] }) {
  return <Scoreboard rallies={list} index={useRallyAt(list).index} />
}

describe('Scoreboard', () => {
  test('seeking into rally 20 shows the score after rally 20', () => {
    const list = rallies(Array.from({ length: 30 }, (_, i) => (i % 3 === 0 ? 'b' : 'a')))
    const clock = createClock()
    render(<ClockContext.Provider value={clock}><BoundScoreboard list={list} /></ClockContext.Provider>)
    expect(screen.getByTestId('points-a')).toHaveTextContent('0') // before the first rally
    act(() => clock.tick(19 * 10 + 3)) // inside rally 20 (idx 19)
    expect(screen.getByTestId('points-a')).toHaveTextContent(String(list[19].score.a))
    expect(screen.getByTestId('points-b')).toHaveTextContent(String(list[19].score.b))
  })
})

describe('RallyList', () => {
  const list = rallies(['a', 'b', 'a'])
  list[1] = { ...list[1], confidence: 0.3 }
  list[2] = { ...list[2], winner_override: 'b', effective_winner: 'b' }

  test('marks current, low-confidence and corrected rallies', () => {
    render(<RallyList rallies={list} currentIndex={0} onSelect={() => {}} />)
    const items = screen.getAllByRole('button')
    expect(items[0]).toHaveAttribute('aria-current', 'true')
    expect(within(items[1]).getByText('Review')).toBeInTheDocument()
    expect(within(items[2]).getByText('edited')).toBeInTheDocument()
    expect(within(items[2]).queryByText('Review')).toBeNull()
  })

  test('each rally has a readable name for screen readers', () => {
    render(<RallyList rallies={list} currentIndex={0} onSelect={() => {}} />)
    expect(screen.getByRole('button', { name: 'Rally 2, won by B, Landed in, at 0:10, confidence 30%, needs review' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rally 3, won by B, Landed in, at 0:20, confidence 90%, edited' })).toBeInTheDocument()
  })

  test('selecting a rally hands it to onSelect', async () => {
    const onSelect = vi.fn()
    render(<RallyList rallies={list} currentIndex={0} onSelect={onSelect} />)
    await userEvent.click(screen.getAllByRole('button')[2])
    expect(onSelect).toHaveBeenCalledWith(list[2])
  })
})

describe('CourtMap', () => {
  test('in and out landings use different markers and name the winner', () => {
    const list = rallies(['a', 'b'])
    list[0] = { ...list[0], landing_x: 4, landing_y: 4 }
    list[1] = { ...list[1], landing_x: 19.2, landing_y: 4 }
    const { container } = render(<CourtMap rallies={list} currentIndex={1} />)
    expect(screen.getByRole('img', { name: 'Rally 1: in, won by A' }).querySelector('circle')).not.toBeNull()
    const out = screen.getByRole('img', { name: 'Rally 2: out, won by B' })
    expect(out.querySelector('path')).not.toBeNull()
    expect(container.querySelectorAll('g[role=img]')).toHaveLength(2)
  })
})

describe('StagePanel', () => {
  test('explains unavailable stages', () => {
    render(<StagePanel stages={[
      { name: 'decode', status: 'done', summary: {} },
      { name: 'court', status: 'unavailable', message: 'court keypoint model not trained yet', summary: {} },
    ]} />)
    expect(screen.getByText('Not available yet')).toBeInTheDocument()
    expect(screen.getByText('court keypoint model not trained yet')).toBeInTheDocument()
  })
})

describe('LayerMenu', () => {
  test('toggles the ball trail; court lines disabled until a court exists', async () => {
    const onChange = vi.fn()
    render(<LayerMenu layers={{ ball: true, court: false, players: false }} onChange={onChange} courtAvailable={false} />)
    await userEvent.click(screen.getByLabelText('Ball trail'))
    expect(onChange).toHaveBeenCalledWith({ ball: false, court: false, players: false })
    expect(screen.getByRole('checkbox', { name: /Court lines/ })).toBeDisabled()
  })
})

describe('RallyList scrolling', () => {
  test('never scrolls the page', () => {
    const spy = vi.spyOn(Element.prototype, 'scrollIntoView')
    const list = rallies(['a', 'b', 'a'])
    const { rerender } = render(<RallyList rallies={list} currentIndex={0} onSelect={() => {}} />)
    rerender(<RallyList rallies={list} currentIndex={2} onSelect={() => {}} />)
    expect(spy).not.toHaveBeenCalled()
  })
})

test('the players layer waits for player tracking and then toggles', async () => {
  const onChange = vi.fn()
  const layers = { ball: true, court: false, players: false }
  const { rerender } = render(<LayerMenu layers={layers} onChange={onChange} courtAvailable={false} />)
  expect(screen.getByRole('checkbox', { name: /Players/ })).toBeDisabled()
  expect(screen.getByText('(available once players are tracked)')).toBeInTheDocument()
  rerender(<LayerMenu layers={layers} onChange={onChange} courtAvailable={false} playersAvailable />)
  await userEvent.click(screen.getByRole('checkbox', { name: /Players/ }))
  expect(onChange).toHaveBeenCalledWith({ ball: true, court: false, players: true })
})
