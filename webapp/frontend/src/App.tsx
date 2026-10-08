import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router'
import { LibraryPage } from './library/LibraryPage'
import { MatchPage } from './match/MatchPage'
import { ThemeSwitch } from './ui/ThemeSwitch'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5_000, refetchOnWindowFocus: false } },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <header className="border-b border-line">
          <div className="mx-auto flex h-12 max-w-6xl items-center gap-6 px-4">
            <span className="text-[15px] font-semibold">Volleyball Analysis</span>
            <nav>
              <NavLink to="/" end className={({ isActive }) => (isActive ? 'text-ink' : 'text-ink-muted hover:text-ink')}>
                Matches
              </NavLink>
            </nav>
            <div className="ml-auto">
              <ThemeSwitch />
            </div>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<LibraryPage />} />
            <Route path="/videos/:id" element={<MatchPage />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
