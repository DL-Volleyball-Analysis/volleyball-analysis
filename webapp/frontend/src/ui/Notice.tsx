import type { ReactNode } from 'react'

/** One-line bordered notice; `title` is the first words, in ink. */
export function Notice({ title, children }: { title: string; children: ReactNode }) {
  return (
    <p role="note" className="rounded border border-line px-3 py-2 text-[13px] text-ink-muted">
      <span className="font-medium text-review">{title}</span> {children}
    </p>
  )
}
