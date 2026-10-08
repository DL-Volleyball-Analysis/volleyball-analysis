import { Fragment } from 'react'

/** File-style names ("final_set_3") may wrap after underscores on narrow screens, never mid-word. */
export function BreakableName({ name }: { name: string }) {
  const parts = name.split('_')
  return (
    <>
      {parts.map((p, i) => (
        <Fragment key={i}>
          {p}
          {i < parts.length - 1 && (
            <>
              _<wbr />
            </>
          )}
        </Fragment>
      ))}
    </>
  )
}
