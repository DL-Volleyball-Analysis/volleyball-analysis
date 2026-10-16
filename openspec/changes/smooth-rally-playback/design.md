# Design

## Context
Measured on the first 90 s of `personal_albert_0920_1_2` with the court from the owner's CVAT label (PRD
`docs/prd/rally-playback.md`): VballNet sees the ball in 52% of frames with 18 jumps over 100 px; WASB gym in 68% with
none. 3D flights are fitted one by one (`vball.trajectory.reconstruct`), 28 kept, with gaps between them; 55 were
rejected over the whole clip. The renderer (`vball_app.render`) draws only the current 3D point and only inside a
flight. 126 player tracks in 90 s, 27 under 1 s; the general detector is used because the player-only one finds too
few people on this footage.

## Decisions

**A rally path is parametrised by its touch points.** A ballistic flight is fully determined by its two end points
and its duration: with touches P_k at times t_k, the flight between them has v0 = (P_k+1 - P_k)/T - g T/2,
T = t_k+1 - t_k. A chain of n flights therefore has 3(n+1) unknowns (the touch points) instead of 6n, and continuity
holds by construction instead of by penalty. The cost is the existing one per flight (Huber reprojection residual),
plus the existing priors moved onto the touch points: hall bounds, player anchors (horizontal distance to the
unambiguous nearest player). Touch times start at the segment boundaries of `segment` and may move by up to two frames
(searched per touch after the first solve). The separate per-flight fits are the initialisation.

**Where to break.** A chain is cut between two flights when the gap without detections around the touch exceeds
`max_gap_s` (default 0.6 s), when the joined fit pushes either flight's median residual above the existing threshold
while the separate fits stay under it (one bad flight must not drag its neighbours), or when the joined solution lies
on a bound. Each part is then solved on its own; a part of one flight is the existing single fit. Breaks carry their
reason. Rejected flights (physically impossible alone) break the chain too.

**Rallies for the path come from the ball, not the rallies stage.** The rallies stage runs after trajectory and
events. A chain is a maximal run of flights joined as above; the touch-role rules start a new count at each chain.
A chain whose first touch lies behind an end line (x < 0 or x > 18 m) starts with a serve; otherwise its first role
is "unknown start" and counting begins at the next net crossing.

**Touch roles are rules over the chain.** Team = side of the net at the touch (x < 9 near-side numbering per
`vball.court`). Net crossings come from the path (x crossing 9 m between touches). Roles: serve; then per possession
1 = receive (after a serve) or dig, 2 = set, 3 = attack; a defending touch within `block_window_s` (default 0.3 s) of
an attack and within 1 m of the net is a block and does not count; touch 4+ is "uncertain". Player = the anchored
player of the touch, else the nearest placed player of that team within 1.5 m in court metres, else none. Confidence
starts from the fit quality of the two flights at the touch and is raised or lowered by the action classifier's event
for that player overlapping the touch. Lives in `vball.touches` (pure functions, unit-tested with hand-written
chains); the events stage (now a placeholder) calls it and writes `touches.json`.

**Ball model by footage.** The ball stage already runs after the court stage. Still camera (`camera_motion` reports no
motion) or court from the gym model or a correction -> WASB gym (`models/wasb_gym.onnx` via `ball_detect.Wasb`, then
`ball_track.track`, processed in chunks of 300 frames for memory); else VballNet V4c. The result names the model. The
broadcast decision for WASB stays in `train-ball-detector` task 3.2.

**Stable tracks.** Still cameras run detection at 15 Hz instead of 10 Hz (players stage config); BoT-SORT's
`track_buffer` scales with the rate so a lost track lives 2 s. After tracking, a re-link pass joins a track that ends
and a track of the same team that starts within 1.5 s and 1.0 m (court metres, box bottom), choosing pairs by
distance; the later track takes the earlier id. The 12-player cap and role check run after re-linking.

**One output for every viewer.** The trajectory stage writes `paths.json`: per chain the frames, positions, observed
flag, per-frame quality, touch frames and breaks. The renderer and the web app boards read it (flights.json stays for
derived values per flight). Drawing: the path from the chain start to now, alpha fading with age, dashed where low
quality; touch markers from `touches.json` with shirt number (or track id) and role.

**Measurement.** `scripts/eval_rally_playback.py` on the five personal clips (courts from the CVAT labels) and the six
fixed clips: ball coverage and jumps, share of rally time (from the rallies stage) with a path position, breaks per
rally, player tracks per player-minute and tracks under 1 s; before (current stage versions, cached) and after.
Touch roles: a labelling page (as `scripts/label_court_points.html`) where the owner marks touches (frame, player box,
role) on at least 20 rallies from clips not used for tuning; accuracy and confusion printed by the same script.

## Risks
- A missed touch merges two flights into one; the joined fit then fails the residual test and breaks there. A later
  improvement is to split a flight at its worst residual and retry.
- A wrong team at a touch near the net (x close to 9 m) shifts the count; the block rule and the "uncertain" role keep
  the error local to one possession.
- 15 Hz detection on still cameras costs about 1.5x the players stage time; acceptable for still cameras, which skip
  the per-frame court work.
- Owner labels are needed for the touch-role number; until then only continuity and track statistics are reported.
