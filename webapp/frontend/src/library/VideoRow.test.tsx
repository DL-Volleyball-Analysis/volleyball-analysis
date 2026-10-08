import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { job, video } from '../test/fixtures'
import { renderApp } from '../test/render'
import { VideoRow } from './VideoRow'

afterEach(() => vi.unstubAllGlobals())

const row = (v = video()) => renderApp(<table><tbody><VideoRow video={v} /></tbody></table>)

describe('VideoRow', () => {
  test('queued', () => {
    row(video({ job: job({ status: 'queued', progress: 0 }) }))
    expect(screen.getByText('Waiting to analyse')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
  })

  test('running shows the stage in plain words and the percentage', () => {
    row(video({ job: job({ status: 'running', stage: 'ball', progress: 0.62 }) }))
    expect(screen.getByText('Tracking the ball')).toBeInTheDocument()
    expect(screen.getByText('62%')).toBeInTheDocument()
  })

  test('failed shows the reason and queues a new analysis', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify(job({ status: 'queued' })), { status: 201 }))
    vi.stubGlobal('fetch', fetch)
    row(video({ job: job({ status: 'failed', error: 'ValueError: cannot open video' }) }))
    expect(screen.getByText(/cannot open video/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Analyse again' }))
    expect(fetch).toHaveBeenCalledWith('/api/videos/v1/jobs', expect.objectContaining({ method: 'POST' }))
  })

  test('done shows the score summary, labelled when it is demo data', () => {
    row(video({ score: { set_no: 2, a: 12, b: 10, sets_a: 1, sets_b: 0, rallies: 47, corrected: 0, demo: true } }))
    expect(screen.getByText("set 2: 12–10")).toBeInTheDocument()
    expect(screen.getByText("(demo data)")).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'final_set3' })).toHaveAttribute('href', '/videos/v1')
    expect(screen.getAllByText('1:40')).toHaveLength(2) // column on wide screens, under the name on narrow ones
  })

  test('done without rallies', () => {
    row()
    expect(screen.getByText('No rallies yet')).toBeInTheDocument()
  })
})
