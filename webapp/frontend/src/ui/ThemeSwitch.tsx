import { useState } from 'react'
import { applyTheme, storedTheme, type Theme } from './theme'

export function ThemeSwitch() {
  const [theme, setTheme] = useState<Theme>(storedTheme)
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={() => {
        applyTheme(next)
        setTheme(next)
      }}
      className="rounded px-2 py-1 text-[13px] text-ink-muted hover:text-ink"
    >
      {next === 'dark' ? 'Dark theme' : 'Light theme'}
    </button>
  )
}
