import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, test } from 'vitest'
import { panelClass } from './panel'
import { Tabs } from './Tabs'

function Harness() {
  const [v, setV] = useState<'a' | 'b'>('a')
  return (
    <>
      <Tabs tabs={[{ id: 'a', label: 'Rallies' }, { id: 'b', label: 'Landings' }]} value={v} onChange={setV} label="Details" />
      <div data-testid="a" className={panelClass(v === 'a')} />
      <div data-testid="b" className={panelClass(v === 'b')} />
    </>
  )
}

test('selecting a tab shows its panel; arrows move between tabs', async () => {
  render(<Harness />)
  expect(screen.getByTestId('b')).toHaveClass('hidden')
  await userEvent.click(screen.getByRole('tab', { name: 'Landings' }))
  expect(screen.getByTestId('b')).toHaveClass('block')
  expect(screen.getByTestId('a')).toHaveClass('hidden')
  await userEvent.keyboard('{ArrowRight}')
  expect(screen.getByRole('tab', { name: 'Rallies' })).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByRole('tab', { name: 'Rallies' })).toHaveFocus()
})
