import type { Team } from '../api/types'

/** The team letter in its colour. Letter first, colour second: never colour alone. */
export function TeamMark({ team }: { team: Team }) {
  return (
    <span className={`font-semibold ${team === 'a' ? 'text-team-a' : 'text-team-b'}`} aria-label={`Team ${team.toUpperCase()}`}>
      {team.toUpperCase()}
    </span>
  )
}
