import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { renderApp } from '../test/render'
import { UploadDrop } from './UploadDrop'

afterEach(() => vi.unstubAllGlobals())

test('rejects a non-video file without calling the API', async () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  renderApp(<UploadDrop />)
  const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })
  await userEvent.upload(screen.getByTestId('file-input'), file, { applyAccept: false })
  expect(await screen.findByText(/is not a supported video type/)).toBeInTheDocument()
  expect(screen.getByText('notes.txt')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

test('uploads a video and reports it as queued', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ id: 'v1' }), { status: 201 })))
  renderApp(<UploadDrop />)
  await userEvent.upload(screen.getByTestId('file-input'), new File(['x'], 'match.mp4', { type: 'video/mp4' }))
  expect(await screen.findByText(/analysis queued/)).toBeInTheDocument()
})

test('shows the server reason when an upload is rejected', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'cannot open video: x.mp4' }), { status: 400 })))
  renderApp(<UploadDrop />)
  await userEvent.upload(screen.getByTestId('file-input'), new File(['x'], 'x.mp4', { type: 'video/mp4' }))
  expect(await screen.findByText(/cannot open video/)).toBeInTheDocument()
})
