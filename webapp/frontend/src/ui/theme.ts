// Per-viewer theme choice. Light is the default; storage can be unavailable (private mode,
// blocked site data), so every access is guarded and falls back to light.
export type Theme = 'light' | 'dark'

const KEY = 'vball-theme'

export function storedTheme(): Theme {
  try {
    return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

export function applyTheme(theme: Theme) {
  if (theme === 'dark') document.documentElement.dataset.theme = 'dark'
  else delete document.documentElement.dataset.theme
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // not persisted; the choice still applies to this page
  }
}
