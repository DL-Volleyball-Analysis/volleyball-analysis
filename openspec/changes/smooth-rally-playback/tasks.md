# Tasks

## 1. Baseline
- [ ] 1.1 Courts of the five personal clips from the CVAT labels as corrections in the app (labels canonically
  numbered; `nva_0929_5` is mirror-numbered); calibration with the labelled net points where floor-only fails
  (`nva_0908_1`)
- [ ] 1.2 `scripts/eval_rally_playback.py`: ball coverage and jumps, path coverage of rally time, breaks per rally,
  player tracks per player-minute and tracks under 1 s; baseline on the personal and fixed clips in
  `docs/results/rally-playback.md`

## 2. Ball model by footage
- [ ] 2.1 Ball stage picks WASB gym for still cameras and gym or corrected courts, VballNet otherwise; chunked
  processing; result names the model; version bump; tests with stub models
- [ ] 2.2 `models/wasb_gym.onnx` in the manifest as a pipeline model; re-measure

## 3. Stable player tracks
- [ ] 3.1 15 Hz detection and longer tracker memory on still cameras (players config)
- [ ] 3.2 Re-link pass (same team, within 1.5 s and 1.0 m) before the 12-player cap; unit tests; version bump;
  re-measure

## 4. Rally path
- [ ] 4.1 Touch-point parametrisation and joint fit of a chain in `vball.trajectory`, priors on touch points, touch
  time refinement; unit tests on synthetic chains
- [ ] 4.2 Breaks (gap, residual worse than separate fits, bound) with reasons; synthetic rally with 30% missed and
  10% false detections: no break, error not worse than separate fits
- [ ] 4.3 Trajectory stage writes `paths.json`; version bump; re-measure coverage and breaks

## 5. Touch roles
- [ ] 5.1 `vball.touches`: team, player, role (serve, receive/dig, set, attack, block, uncertain), confidence; unit
  tests from hand-written chains (spec scenarios)
- [ ] 5.2 Events stage outputs `touches.json`; classifier agreement adjusts confidence; version bump
- [ ] 5.3 Touch labelling page; owner labels at least 20 rallies; role and player accuracy in the results

## 6. Drawing
- [ ] 6.1 Renderer: path up to now with fading, dashed low quality, gaps at breaks, touch markers with player and role
- [ ] 6.2 Web app 2D and 3D boards read `paths.json` and `touches.json`; frontend tests
- [ ] 6.3 Rendered videos of two personal clips for the owner's review

## 7. Wrap-up
- [ ] 7.1 CHANGELOG, README results, papers (3D chain and touch roles), `openspec validate smooth-rally-playback --strict`
