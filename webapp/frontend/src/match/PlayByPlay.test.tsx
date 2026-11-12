import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test } from 'vitest'
import type { ActionEvent } from '../api/types'
import { ClockContext, createClock } from '../playback/clock'
import { rallies } from '../test/fixtures'
import { renderApp } from '../test/render'
import { PlayByPlay } from './PlayByPlay'

const act = (action: ActionEvent['action'], start_s: number, number: number | null, team: 'a' | 'b' | null): ActionEvent =>
  ({ action, track_id: 5, start_s, end_s: start_s + 0.3, peak_conf: 0.9, number, team })

test('lists the rally actions in order, filters by kind and seeks on click', async () => {
  const clock = createClock()
  const video = document.createElement('video')
  clock.attach(video)
  const rally = { ...rallies(['a'])[0], start_s: 10, end_s: 16 }
  const actions = [act('spike', 14, 2, 'b'), act('serve', 9.8, 7, 'a'), act('receive', 11, null, 'b'), act('set', 30, 4, 'a')]
  renderApp(<ClockContext.Provider value={clock}><PlayByPlay rally={rally} actions={actions} /></ClockContext.Provider>)
  const rows = () => screen.getAllByRole('listitem').map((li) => li.textContent)
  expect(rows()).toEqual([expect.stringContaining('Serve#7A'), expect.stringContaining('ReceiveID 5B'), expect.stringContaining('Attack#2B')])
  expect(screen.queryByRole('button', { name: 'Set' })).not.toBeInTheDocument() // no set in this rally: no chip
  await userEvent.click(screen.getByRole('button', { name: 'Attack' }))
  expect(rows()).toHaveLength(1)
  await userEvent.click(screen.getByRole('button', { name: /Attack by #2 of team B/ }))
  expect(video.currentTime).toBe(14)
})

test('says so when a rally has no recognised action', () => {
  const rally = { ...rallies(['a'])[0], start_s: 0, end_s: 3 }
  renderApp(<ClockContext.Provider value={createClock()}><PlayByPlay rally={rally} actions={[]} /></ClockContext.Provider>)
  expect(screen.getByText('No actions recognised in this rally.')).toBeInTheDocument()
})


test('Whole match lists every action, also outside the rally', async () => {
  const rally = { ...rallies(['a'])[0], start_s: 10, end_s: 16 }
  const actions = [act('spike', 14, 2, 'b'), act('set', 30, 4, 'a')]
  renderApp(<ClockContext.Provider value={createClock()}><PlayByPlay rally={rally} actions={actions} /></ClockContext.Provider>)
  expect(screen.getAllByRole('listitem')).toHaveLength(1)
  await userEvent.click(screen.getByRole('button', { name: 'Whole match' }))
  expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual([expect.stringContaining('Attack'), expect.stringContaining('Set#4')])
})
