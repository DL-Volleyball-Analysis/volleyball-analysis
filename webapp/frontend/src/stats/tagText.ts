import type { Outcome, Tag, TagKind } from '../api/types'

export const KIND_LABEL: Record<TagKind, string> = { attack: 'Attack', serve: 'Serve' }

export const OUTCOME_LABEL: Record<Tag['effective_outcome'], string> = {
  kill: 'kill', ace: 'ace', error: 'error', in_play: 'in play', unknown: 'unknown (no winner yet)', outside: 'outside rallies',
}

export const OUTCOMES: Record<TagKind, Outcome[]> = { attack: ['kill', 'error', 'in_play'], serve: ['ace', 'error', 'in_play'] }

/** "Attack by A 10, kill (from the winner)" — for titles and screen readers. */
export function tagLabel(t: Tag): string {
  const fromWinner = t.inferred && ['kill', 'ace', 'error', 'unknown'].includes(t.effective_outcome)
  const how = !t.inferred ? ' (set by you)' : fromWinner ? ' (from the winner)' : ''
  return `${KIND_LABEL[t.kind]} by ${t.team.toUpperCase()} ${t.number}, ${OUTCOME_LABEL[t.effective_outcome]}${how}`
}
