import { useCallback, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useJobStream } from '../api/jobStream'
import { useAddTag, useCorrectRally, useDeleteTag, usePatchTag, useRallies, useStages, useTags, useVideo } from '../api/queries'
import type { Rally, Tag, TagKind, Team } from '../api/types'
import { BoardPanel } from '../board/BoardPanel'
import { CourtMap } from '../court/CourtMap'
import { ClockContext, createClock, useClock } from '../playback/clock'
import { useRallyAt } from '../playback/useRallyAt'
import { StatsPanel } from '../stats/StatsPanel'
import { TagEntry } from '../stats/TagEntry'
import { TagInspector } from '../stats/TagInspector'
import { useTagShortcuts } from '../stats/useTagShortcuts'
import { BreakableName } from '../ui/BreakableName'
import { Notice } from '../ui/Notice'
import { Tabs } from '../ui/Tabs'
import { panelClass } from '../ui/panel'
import { STAGE_LABEL } from '../ui/format'
import { LayerMenu } from './LayerMenu'
import type { Layers } from './OverlayCanvas'
import { RallyList } from './RallyList'
import { MatchTimeline } from './MatchTimeline'
import { RallyInspector } from './RallyInspector'
import { Scoreboard } from './Scoreboard'
import { StagePanel } from './StagePanel'
import { VideoStage } from './VideoStage'
import { useReviewShortcuts } from './useReviewShortcuts'

const NO_RALLIES: Rally[] = []
const NO_TAGS: Tag[] = []

type Panel = 'rallies' | 'board' | 'stats' | 'court' | 'stages'
const PANELS: { id: Panel; label: string }[] = [
  { id: 'rallies', label: 'Rallies' },
  { id: 'board', label: 'Board' },
  { id: 'stats', label: 'Stats' },
  { id: 'court', label: 'Landings' },
  { id: 'stages', label: 'Analysis' },
]

function MatchView({ id }: { id: string }) {
  const clock = useClock()
  const video = useVideo(id)
  const ralliesQ = useRallies(id)
  const stages = useStages(id)
  useJobStream(video.data)
  const rallies = ralliesQ.data ?? NO_RALLIES
  const pos = useRallyAt(rallies)
  const correction = useCorrectRally(id)
  const [layers, setLayers] = useState<Layers>({ ball: true, court: false })
  const [panel, setPanel] = useState<Panel>('rallies')
  const tags = useTags(id).data ?? NO_TAGS
  const addTag = useAddTag(id)
  const patchTag = usePatchTag(id)
  const deleteTag = useDeleteTag(id)
  const [entry, setEntry] = useState<{ kind: TagKind; timeS: number } | null>(null)
  const [lastTeam, setLastTeam] = useState<Team>('a')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  const seekTo = useCallback((r: Rally) => clock.seek(r.start_s), [clock])
  const correct = useCallback((idx: number, winner: Team | null) => correction.mutate({ idx, winner }), [correction])
  useReviewShortcuts({ rallies, index: pos.index, clock, correct })
  const startTag = useCallback((kind: TagKind, timeS: number) => {
    setSelectedTag(null)
    setEntry({ kind, timeS })
  }, [])
  useTagShortcuts({ clock, onStart: startTag })
  const saveTag = (team: Team, number: number) => {
    if (!entry) return
    addTag.mutate({ time_s: entry.timeS, kind: entry.kind, team, number }, { onSuccess: () => setEntry(null) })
    setLastTeam(team)
  }
  const selectTag = useCallback((t: Tag) => {
    setEntry(null)
    setSelectedTag(t.id)
    clock.seek(t.time_s)
  }, [clock])
  const tag = tags.find((t) => t.id === selectedTag)
  const tagError = addTag.error ?? patchTag.error ?? deleteTag.error

  if (video.isPending) return <p className="text-ink-muted">Loading match…</p>
  if (video.isError) return <p className="text-review">Could not load this match: {video.error.message}</p>

  const v = video.data
  const duration = v.frames && v.fps ? v.frames / v.fps : 0
  const demo = rallies.some((r) => r.source === 'demo')
  const courtAvailable = stages.data?.find((s) => s.name === 'court')?.status === 'done'
  const running = v.job && (v.job.status === 'queued' || v.job.status === 'running')

  return (
    <div className="space-y-3">
      {demo && <Notice title="Demo data.">These rallies are placeholders, not analysis results; rally detection arrives with milestone M3.</Notice>}
      {correction.isError && <Notice title="Not saved.">{correction.error.message}. The previous winner was restored.</Notice>}
      {tagError && <Notice title="Tag not saved.">{tagError.message}</Notice>}

      <div className="overflow-hidden rounded-[10px] border border-line bg-window shadow-[var(--shadow-window)]">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-line bg-panel px-4 py-2.5">
          <div className="min-w-0">
            <h1 className="font-mono text-[13px] font-medium">
              <BreakableName name={v.name} />
            </h1>
            {running && (
              <p className="text-[12px] text-ink-muted">
                Analysing: {v.job?.stage ? STAGE_LABEL[v.job.stage] : 'waiting'} {Math.round((v.job?.progress ?? 0) * 100)}%
              </p>
            )}
          </div>
          <Scoreboard rallies={rallies} index={pos.index} />
        </div>

        <div className="grid lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div className="min-w-0">
            <VideoStage video={v} layers={layers} />
            <div className="border-t border-line px-3 py-2">
              <LayerMenu layers={layers} onChange={setLayers} courtAvailable={courtAvailable} />
            </div>
          </div>
          <aside className="border-t border-line lg:border-t-0 lg:border-l">
            {(entry || tag) && (
              <div className="border-b border-line px-4 py-3">
                {entry ? (
                  <TagEntry kind={entry.kind} timeS={entry.timeS} defaultTeam={lastTeam} saving={addTag.isPending}
                    onSave={saveTag} onCancel={() => setEntry(null)} />
                ) : tag ? (
                  <TagInspector tag={tag}
                    onOutcome={(outcome) => patchTag.mutate({ tagId: tag.id, patch: { outcome } })}
                    onDelete={() => deleteTag.mutate(tag.id, { onSuccess: () => setSelectedTag(null) })}
                    onClose={() => setSelectedTag(null)} />
                ) : null}
              </div>
            )}
            <div className="px-4 pt-3 pb-4">
              <h2 className="mb-1 text-[13px] font-semibold">Rally</h2>
              <RallyInspector rallies={rallies} index={pos.index} onCorrect={correct} />
            </div>
            <div className="border-t border-line px-4 pb-4">
              <Tabs tabs={PANELS} value={panel} onChange={setPanel} label="Match details" />
              <section id="panel-rallies" role="tabpanel" aria-labelledby="tab-rallies" className={`pt-3 ${panelClass(panel === 'rallies')}`}>
                <RallyList rallies={rallies} currentIndex={pos.index} onSelect={seekTo} />
              </section>
              <section id="panel-board" role="tabpanel" aria-labelledby="tab-board" className={`pt-3 ${panelClass(panel === 'board')}`}>
                {panel === 'board' && (
                  <BoardPanel videoId={v.id} rally={rallies[pos.index]} trajectory={stages.data?.find((s) => s.name === 'trajectory')} />
                )}
              </section>
              <section id="panel-stats" role="tabpanel" aria-labelledby="tab-stats" className={`pt-3 ${panelClass(panel === 'stats')}`}>
                {panel === 'stats' && <StatsPanel videoId={v.id} />}
              </section>
              <section id="panel-court" role="tabpanel" aria-labelledby="tab-court" className={`pt-3 ${panelClass(panel === 'court')}`}>
                <CourtMap rallies={rallies} currentIndex={pos.index} />
              </section>
              <section id="panel-stages" role="tabpanel" aria-labelledby="tab-stages" className={`pt-1 ${panelClass(panel === 'stages')}`}>
                {stages.data ? <StagePanel stages={stages.data} /> : <p className="py-2 text-ink-muted">Loading…</p>}
              </section>
            </div>
          </aside>
        </div>

        <div className="border-t border-line">
          <MatchTimeline videoId={v.id} rallies={rallies} duration={duration} currentIndex={pos.index} onSelect={seekTo}
            tags={tags} selectedTag={selectedTag} onSelectTag={selectTag} />
        </div>
      </div>

      <p className="hidden text-[12px] text-ink-muted md:block">
        <kbd>J</kbd> / <kbd>K</kbd> previous / next rally, <kbd>Space</kbd> play or pause, <kbd>1</kbd> / <kbd>2</kbd> winner A / B, <kbd>0</kbd> clear correction, <kbd>T</kbd> / <kbd>S</kbd> tag an attack / serve. Click or drag the timeline to seek.
      </p>
    </div>
  )
}

export function MatchPage() {
  const { id = '' } = useParams()
  const clock = useMemo(() => createClock(), [])
  return (
    <ClockContext.Provider value={clock}>
      <div className="mx-auto max-w-6xl px-4 py-5">
        <nav aria-label="Breadcrumb" className="mb-2 text-[13px] text-ink-muted">
          <Link to="/" className="hover:text-ink">Matches</Link>
        </nav>
        <MatchView id={id} />
      </div>
    </ClockContext.Provider>
  )
}
