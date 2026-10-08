import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { TagEntry } from './TagEntry'

function entry(defaultTeam: 'a' | 'b' = 'a') {
  const onSave = vi.fn()
  const onCancel = vi.fn()
  render(<TagEntry kind="attack" timeS={12.34} defaultTeam={defaultTeam} onSave={onSave} onCancel={onCancel} />)
  return { onSave, onCancel, input: screen.getByRole('textbox', { name: 'Player number' }) }
}

test('the number field has focus: number and Enter save with the default team', async () => {
  const { onSave, input } = entry('b')
  expect(input).toHaveFocus()
  expect(screen.getByText('at 0:12.3')).toBeInTheDocument()
  await userEvent.keyboard('10{Enter}')
  expect(onSave).toHaveBeenCalledWith('b', 10)
})

test('A / B switch the team without typing into the number', async () => {
  const { onSave, input } = entry('a')
  await userEvent.keyboard('1b2{Enter}')
  expect(input).toHaveValue('12')
  expect(screen.getByRole('button', { name: 'B' })).toHaveAttribute('aria-pressed', 'true')
  expect(onSave).toHaveBeenCalledWith('b', 12)
})

test('Enter without a number does nothing; Esc cancels; only digits are kept', async () => {
  const { onSave, onCancel, input } = entry()
  await userEvent.keyboard('{Enter}')
  expect(onSave).not.toHaveBeenCalled()
  await userEvent.type(input, 'x7y')
  expect(input).toHaveValue('7')
  await userEvent.keyboard('{Escape}')
  expect(onCancel).toHaveBeenCalled()
})
