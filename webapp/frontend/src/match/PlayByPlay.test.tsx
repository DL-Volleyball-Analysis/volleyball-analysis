import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act as act_ } from 'react'
import { expect, test, vi } from 'vitest'
import type { ActionEvent } from '../api/types'
import { ClockContext, createClock } from '../playback/clock'
import { rallies } from '../test/fixtures'
import { renderApp } from '../test/render'
import { PlayByPlay } from './PlayByPlay'
import { CLIP_LEAD_S, CLIP_TAIL_S, advance } from './playlist'

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

test('filters by player and plays the filtered actions one after another', async () => {
  const clock = createClock()
  const video = document.createElement('video')
  const play = vi.spyOn(video, 'play').mockResolvedValue(undefined)
  vi.spyOn(video, 'pause').mockImplementation(() => video.dispatchEvent(new Event('pause')))
  Object.defineProperty(video, 'paused', { get: () => true })
  clock.attach(video)
  const rally = { ...rallies(['a'])[0], start_s: 10, end_s: 30 }
  const actions = [act('serve', 11, 7, 'a'), act('receive', 12, 3, 'b'), act('spike', 20, 7, 'a')]
  renderApp(<ClockContext.Provider value={clock}><PlayByPlay rally={rally} actions={actions} /></ClockContext.Provider>)
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player' }), 'a #7')
  expect(screen.getAllByRole('listitem')).toHaveLength(2)
  await userEvent.click(screen.getByRole('button', { name: /Play these \(2\)/ }))
  expect(video.currentTime).toBe(11 - CLIP_LEAD_S)
  expect(play).toHaveBeenCalled()
  video.currentTime = 11 + CLIP_TAIL_S + 0.1 // the first clip is over
  act_(() => { video.dispatchEvent(new Event('timeupdate')) })
  await vi.waitFor(() => expect(video.currentTime).toBe(20 - CLIP_LEAD_S))
  expect(screen.getByRole('button', { name: /Stop \(2 of 2\)/ })).toBeInTheDocument()
  video.currentTime = 20 + CLIP_TAIL_S + 0.1 // the last one: the list stops
  act_(() => { video.dispatchEvent(new Event('timeupdate')) })
  await vi.waitFor(() => expect(screen.getByRole('button', { name: /Play these/ })).toBeInTheDocument())
})

test('overlapping clips play through; a gap seeks; the list ends after the last clip', () => {
  const list = [act('serve', 1, 1, 'a'), act('receive', 2, 2, 'b'), act('set', 9, 2, 'b')]
  expect(advance(list, 0, 1.5)).toEqual({ at: 0, seek: false })
  expect(advance(list, 0, 2.1)).toEqual({ at: 1, seek: false }) // the receive is reached while the serve plays
  expect(advance(list, 1, 2 + CLIP_TAIL_S)).toEqual({ at: 2, seek: true }) // 7.5 s is ahead: jump
  expect(advance(list, 2, 9 + CLIP_TAIL_S)).toBeNull()
})

test('a re-render during playback (the rally moves on) neither re-seeks nor changes the playing list', async () => {
  const clock = createClock()
  const video = document.createElement('video')
  vi.spyOn(video, 'play').mockResolvedValue(undefined)
  Object.defineProperty(video, 'paused', { get: () => true })
  clock.attach(video)
  const first = { ...rallies(['a'])[0], start_s: 10, end_s: 15 }
  const actions = [act('serve', 11, 7, 'a'), act('spike', 14, 7, 'a'), act('set', 40, 2, 'b')]
  const view = renderApp(<ClockContext.Provider value={clock}><PlayByPlay rally={first} actions={actions} /></ClockContext.Provider>)
  await userEvent.click(screen.getByRole('button', { name: /Play these \(2\)/ }))
  video.currentTime = 11.5 // playing inside the first clip
  view.rerender(<ClockContext.Provider value={clock}><PlayByPlay rally={{ ...first, idx: 1, start_s: 38, end_s: 42 }} actions={actions} /></ClockContext.Provider>)
  expect(video.currentTime).toBe(11.5)
  expect(screen.getAllByRole('listitem')).toHaveLength(2)
})
