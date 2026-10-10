import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import type { Suggestion } from '../api/types'
import { SuggestionCard } from './SuggestionCard'

const known: Suggestion = { id: 'attack-100-3', kind: 'attack', time_s: 12.3, team: 'a', number: 10, track_id: 3, status: 'open' }

function card(s: Suggestion) {
  const onAccept = vi.fn(), onDismiss = vi.fn(), onClose = vi.fn()
  render(<SuggestionCard suggestion={s} onAccept={onAccept} onDismiss={onDismiss} onClose={onClose} />)
  return { onAccept, onDismiss, onClose }
}

test('a suggestion with team and number is accepted as it stands', async () => {
  const { onAccept } = card(known)
  expect(screen.getByRole('heading', { name: 'Suggested attack' })).toBeInTheDocument()
  expect(screen.getByText(/Not counted until accepted/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Accept' }))
  expect(onAccept).toHaveBeenCalledWith('a', 10)
})

test('without a read number the coach must give it before accepting', async () => {
  const { onAccept } = card({ ...known, number: null })
  const accept = screen.getByRole('button', { name: 'Accept' })
  expect(accept).toBeDisabled()
  expect(screen.getByText(/Shirt number not read/)).toBeInTheDocument()
  await userEvent.type(screen.getByRole('textbox', { name: 'Number' }), '7x')
  expect(screen.getByRole('textbox', { name: 'Number' })).toHaveValue('7')
  await userEvent.click(accept)
  expect(onAccept).toHaveBeenCalledWith('a', 7)
})

test('dismiss and close', async () => {
  const { onDismiss, onClose } = card(known)
  await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
  await userEvent.click(screen.getByRole('button', { name: 'Close' }))
  expect(onDismiss).toHaveBeenCalledOnce()
  expect(onClose).toHaveBeenCalledOnce()
})
