import type { Rally } from '../api/types'

/** Rallies below this confidence (and not corrected by the user) are flagged for review. */
export const REVIEW_THRESHOLD = 0.6

export const needsReview = (r: Rally) => r.winner_override == null && (r.confidence ?? 0) < REVIEW_THRESHOLD

const REASONS: Record<string, string> = {
  in: 'Landed in',
  out: 'Out',
  net: 'Net',
  fault: 'Fault',
  unknown: 'Unclear',
}

export const reasonText = (r: Rally) => REASONS[r.reason ?? 'unknown'] ?? r.reason ?? 'Unclear'
