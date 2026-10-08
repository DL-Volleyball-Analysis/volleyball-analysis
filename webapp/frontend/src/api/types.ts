// Names for the API shapes. Generated from the backend's OpenAPI schema: run `npm run gen:api`
// after changing backend models; never edit schema.d.ts or hand-write response types.
import type { components } from './schema'

type S = components['schemas']

export type Video = S['Video']
export type Job = S['Job']
export type StageInfo = S['StageInfo']
export type Rally = S['Rally']
export type Score = S['Score']
export type BallWindow = S['BallWindow']
export type Team = NonNullable<Rally['winner']>
export type StageName = StageInfo['name']
export type ScoreSummary = S['ScoreSummary']
export type BallCoverage = S['BallCoverage']
export type Tag = S['TagOut']
export type TagIn = S['TagIn']
export type TagPatch = S['TagPatch']
export type TagKind = Tag['kind']
export type Outcome = NonNullable<Tag['outcome']>
export type RosterPlayer = S['RosterPlayer']
export type Stats = S['Stats']
export type StatLine = S['StatLine']
