import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { App } from './App'

afterEach(() => vi.unstubAllGlobals())

test('opens on the library', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('[]', { status: 200 })))
  render(<App />)
  expect(screen.getByRole('heading', { name: 'Matches' })).toBeInTheDocument()
  expect(await screen.findByText(/No matches yet/)).toBeInTheDocument()
})
