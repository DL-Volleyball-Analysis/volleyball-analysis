import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { ThemeSwitch } from './ThemeSwitch'
import { storedTheme } from './theme'

afterEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.theme
  vi.restoreAllMocks()
})

test('light by default; switching to dark is applied and remembered', async () => {
  render(<ThemeSwitch />)
  expect(document.documentElement.dataset.theme).toBeUndefined()
  await userEvent.click(screen.getByRole('button', { name: 'Dark theme' }))
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(storedTheme()).toBe('dark')
  expect(screen.getByRole('button', { name: 'Light theme' })).toBeInTheDocument()
})

test('falls back to light when storage is blocked', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('blocked')
  })
  expect(storedTheme()).toBe('light')
})
