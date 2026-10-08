import type { Layers } from './OverlayCanvas'

export function LayerMenu({ layers, onChange, courtAvailable, playersAvailable = false }: {
  layers: Layers
  onChange: (l: Layers) => void
  courtAvailable: boolean
  playersAvailable?: boolean
}) {
  return (
    <fieldset className="flex flex-wrap gap-x-5 gap-y-1 text-[13px] [&_input]:accent-[var(--accent)]">
      <legend className="sr-only">Overlays</legend>
      <label className="flex items-center gap-1.5">
        <input type="checkbox" checked={layers.ball} onChange={(e) => onChange({ ...layers, ball: e.target.checked })} />
        Ball trail
      </label>
      <label className={`flex items-center gap-1.5 ${courtAvailable ? '' : 'text-ink-muted'}`}>
        <input
          type="checkbox"
          checked={courtAvailable && layers.court}
          disabled={!courtAvailable}
          onChange={(e) => onChange({ ...layers, court: e.target.checked })}
        />
        Court lines
        {!courtAvailable && <span>(available once the court is found)</span>}
      </label>
      <label className={`flex items-center gap-1.5 ${playersAvailable ? '' : 'text-ink-muted'}`}>
        <input
          type="checkbox"
          checked={playersAvailable && layers.players}
          disabled={!playersAvailable}
          onChange={(e) => onChange({ ...layers, players: e.target.checked })}
        />
        Players
        {!playersAvailable && <span>(available once players are tracked)</span>}
      </label>
    </fieldset>
  )
}
