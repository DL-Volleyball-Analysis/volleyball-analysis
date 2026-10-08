import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import type { StatLine, Stats } from '../api/types'
import { fakeApi } from '../test/fakeApi'
import { renderApp } from '../test/render'
import { StatsPanel } from './StatsPanel'
import { ratio } from './statsText'

const line = (p: Partial<StatLine>): StatLine => ({
  team: 'a', number: 10, name: null, set_no: null, attempts: 0, kills: 0, attack_errors: 0, efficiency: null,
  kill_rate: null, serves: 0, aces: 0, serve_errors: 0, unknown: 0, incomplete: false, ...p,
})

// the fixture match of tests/test_stats.py, as the API returns it
const STATS: Stats = {
  rallies: 5, tagged_rallies: 5, outside: 1,
  lines: [
    line({ number: 4, set_no: 1, attempts: 1, kills: 1, efficiency: 1, kill_rate: 1 }),
    line({ number: 4, attempts: 1, kills: 1, efficiency: 1, kill_rate: 1 }),
    line({ number: 10, name: 'Wu', set_no: 1, attempts: 4, kills: 1, attack_errors: 2, efficiency: -1 / 3, kill_rate: 1 / 3, unknown: 1, incomplete: true }),
    line({ number: 10, name: 'Wu', attempts: 4, kills: 1, attack_errors: 2, efficiency: -1 / 3, kill_rate: 1 / 3, unknown: 1, incomplete: true }),
    line({ number: null, set_no: 1, attempts: 5, kills: 2, attack_errors: 2, efficiency: 0, kill_rate: 0.5, serves: 1, unknown: 1, incomplete: true }),
    line({ number: null, attempts: 5, kills: 2, attack_errors: 2, efficiency: 0, kill_rate: 0.5, serves: 1, unknown: 1, incomplete: true }),
    line({ team: 'b', number: 3, set_no: 1, serves: 1 }),
    line({ team: 'b', number: 3, set_no: 2, serves: 1, aces: 1 }),
    line({ team: 'b', number: 3, serves: 2, aces: 1 }),
    line({ team: 'b', number: null, set_no: 1, serves: 1 }),
    line({ team: 'b', number: null, set_no: 2, serves: 1, aces: 1 }),
    line({ team: 'b', number: null, serves: 2, aces: 1 }),
  ],
}

let rosterStatus = 200

function setup(stats: Stats = STATS) {
  return fakeApi({
    'GET /api/videos/v1/stats': () => ({ body: stats }),
    'GET /api/videos/v1/roster': () => ({ body: { players: [{ team: 'a', number: 10, name: 'Wu' }] } }),
    'PUT /api/videos/v1/roster': (init) =>
      rosterStatus === 200 ? { body: JSON.parse(String(init?.body)) } : { status: 400, body: { detail: 'number 7 is listed twice for team A' } },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
  rosterStatus = 200
})

test('ratios: three decimals without the leading zero, a dash when nothing is decided', () => {
  expect([ratio(0.2), ratio(-1 / 3), ratio(1), ratio(0), ratio(null)]).toEqual(['.200', '-.333', '1.000', '.000', '–'])
})

test('match tables per team with incomplete marks, outside tags and the CSV link', async () => {
  setup()
  renderApp(<StatsPanel videoId="v1" />)
  const a = (await screen.findByRole('table', { name: /Team A/ }))
  const wu = within(a).getByRole('row', { name: /^10 Wu \*/ })
  expect(within(wu).getAllByRole('cell').map((c) => c.textContent)).toEqual(['4', '1', '2', '-.333', '.333', '0', '0', '0'])
  expect(within(wu).getByTitle('1 tag(s) without an outcome yet')).toHaveTextContent('*')
  expect(within(a).getByRole('row', { name: /^Team/ })).toHaveTextContent('.000')
  expect(screen.getByText(/5 of 5 rallies tagged\. 1 tag\(s\) outside rallies are not counted\./)).toBeInTheDocument()
  expect(screen.getByText(/left out of the ratios/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Export CSV' })).toHaveAttribute('href', '/api/videos/v1/stats?format=csv')
})

test('the set filter shows one set', async () => {
  setup()
  renderApp(<StatsPanel videoId="v1" />)
  await screen.findByRole('table', { name: /Team A/ })
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Show' }), '2')
  expect(screen.queryByRole('table', { name: /Team A/ })).not.toBeInTheDocument() // no team A tags in set 2
  const b = screen.getByRole('table', { name: /Team B/ })
  expect(within(within(b).getByRole('row', { name: /^3/ })).getAllByRole('cell')[6]).toHaveTextContent('1')
})

test('without tags it explains how to tag', async () => {
  setup({ rallies: 3, tagged_rallies: 0, outside: 0, lines: [] })
  renderApp(<StatsPanel videoId="v1" />)
  expect(await screen.findByText(/Press/)).toHaveTextContent('Tag every attack')
})

test('the roster editor shows the server message for a duplicate number', async () => {
  rosterStatus = 400
  const fetch = setup()
  renderApp(<StatsPanel videoId="v1" />)
  await userEvent.click(await screen.findByRole('button', { name: 'Edit roster' }))
  const roster = screen.getByRole('region', { name: 'Roster' })
  expect(within(roster).getByRole('textbox', { name: 'Team A player 1 name' })).toHaveValue('Wu')
  await userEvent.click(within(roster).getAllByRole('button', { name: 'Add player' })[0])
  await userEvent.type(within(roster).getByRole('textbox', { name: 'Team A player 2 number' }), '10')
  await userEvent.click(within(roster).getByRole('button', { name: 'Save roster' }))
  expect(await within(roster).findByRole('alert')).toHaveTextContent('number 7 is listed twice for team A')
  const put = fetch.mock.calls.find(([, init]) => init?.method === 'PUT')!
  expect(JSON.parse(String(put[1]?.body))).toEqual({
    players: [{ team: 'a', number: 10, name: 'Wu' }, { team: 'a', number: 10, name: null }],
  })
  await waitFor(() => expect(screen.getByRole('region', { name: 'Roster' })).toBeInTheDocument()) // stays open
})
