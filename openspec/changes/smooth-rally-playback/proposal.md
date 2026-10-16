# Proposal

## Why

On the owner's amateur recording the analysis video shows a flickering ball on the 2D map and in 3D, flickering
player boxes, and no answer to "who served, received, set and attacked" (PRD `docs/prd/rally-playback.md`). The 3D
flights are fitted one by one with gaps between them, the renderer draws only the current point, VballNet loses the
ball half the time on gym footage, and players lose their track at 10 Hz detection.

## What Changes

- **Connected rally path** (`vball.trajectory`): consecutive flights of a rally are fitted jointly so that each touch is
  one 3D point at one time; frames between flights get positions from the fitted paths; a link that cannot be fitted
  breaks the path with a reason. Trajectory stage version bump.
- **Touch roles** (new `vball.touches`, events stage): every touch gets its team (side of the net), player (anchor or
  nearest placed player) and role from the sequence rules (serve; receive or dig, set, attack per possession; block at
  the net). The action classifier only adjusts confidence. The events stage, today a placeholder, outputs these
  touches.
- **Ball model by footage**: still cameras and gym footage use WASB gym weights; broadcast keeps VballNet. Ball stage
  version bump.
- **Stable player tracks**: still cameras detect at 15 Hz, the tracker keeps lost tracks longer, and a new track that
  starts where a lost one ended (same court position, within a short time) takes over its id. Players stage version
  bump.
- **Drawing**: the rendered video's 2D map and 3D view and the web app's tactics boards draw the rally path up to
  now with fading, touch markers with player and role, dashed low-quality parts.
- **Measurement**: `scripts/eval_rally_playback.py` reports continuity, ball and track statistics on the personal and
  fixed clips; a touch labelling page for owner labels; touch-role accuracy in `docs/results/rally-playback.md`.

## Capabilities

### New Capabilities
- `rally-touches`: touches with team, player and role from the sequence of a rally.

### Modified Capabilities
- `ball-trajectory-3d`: flights of a rally are joined at touches into one path.
- `ball-tracking`: the ball model is chosen by footage type.
- `player-tracking`: higher detection rate on still cameras and re-linking of lost tracks.
- `tactics-board`: the board draws the rally path up to the current time and the touches.

## Impact

- Code: `src/vball/trajectory/`, new `src/vball/touches.py`, `src/vball/pipeline/stages/{ball,players,trajectory,
  events}.py`, `src/vball/players.py`, `webapp/backend/vball_app/render.py`, `webapp/frontend/src/board/`, new
  evaluation script and labelling page.
- Stage versions: ball, players, trajectory, events; cached results are recomputed from the ball stage on.
- Models: `models/wasb_gym.onnx` joins the manifest as a pipeline model.
- Related: `train-ball-detector` (broadcast decision stays there), `add-player-reid` (ids across rallies),
  `add-labelling-loop` (courts of the personal clips).
