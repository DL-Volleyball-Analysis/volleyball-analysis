# Tasks

## 1. Data and evaluation

- [ ] 1.1 Download the SportsMOT volleyball sequences into `data/datasets/sportsmot/` (record source, license CC BY-NC 4.0, and split sizes in a README there) and verify the annotation files load with frame and id counts printed
- [ ] 1.2 Clone TrackEval unmodified into `external/` and write `scripts/eval_player_tracking.py`; verify it reproduces a perfect score when fed the ground truth as predictions
- [ ] 1.3 Run the baseline grid (YOLO26 n / s, 960 / 1280 px, BoT-SORT / ByteTrack, 10 fps) on the validation sequences and record HOTA, IDF1, MOTA, recall, precision and CPU ms/frame in `docs/results/player-tracking.md`; verify every number in the file matches the script output
- [ ] 1.4 Measure IDF1 and time at 30 / 10 / 5 fps for the best configuration and choose the default rate; record the choice and why

## 2. `vball.players`

- [ ] 2.1 Implement detection + tracking at a configurable rate with linear box interpolation between samples; verify unit tests with a fake detector for id continuity and interpolation
- [ ] 2.2 Implement the on-court filter, court position and side of net from a court mapping, and the "unavailable" path without one; verify tests with a synthetic homography (referee outside the margins dropped, server behind the end line kept)
- [ ] 2.3 Document the module and the `players.csv.gz` columns in its docstring and verify the tests pass

## 3. Pipeline and API (web app)

- [ ] 3.1 Add the `players` stage between `ball` and `events`, bump the events stage version, and verify backend tests for stage order, reuse and the no-court path
- [ ] 3.2 Add `GET /videos/{id}/players?start=&end=` and verify API tests for windowing and the 404 before the stage ran; regenerate frontend types
- [ ] 3.3 Measure the stage time on the 5 evaluation clips and verify it against the PRD budget (scaled to a 2-hour match); record it

## 4. Overlay (web app)

- [ ] 4.1 Draw player boxes with track ids on the overlay canvas from windowed player data and add a "Players" toggle (off by default); verify overlay tests with the fake canvas and that toggling stops drawing
- [ ] 4.2 Verify by screenshot that boxes sit on the players after a resize, in both themes

## 5. Fine-tuning (only if 1.3 misses the PRD targets)

- [ ] 5.1 Decide from 1.3: if targets are met, record "not needed" with the numbers and mark 5.2-5.3 not applicable in this file; otherwise continue
- [ ] 5.2 Colab notebook fine-tuning the detector on SportsMOT volleyball training sequences with checkpoints and resume on Drive; verify a 1-epoch local smoke run
- [ ] 5.3 Re-run 1.3 with the fine-tuned weights and record both results side by side

## 6. Docs

- [ ] 6.1 Update README status, CLAUDE.md and the PRD acceptance numbers (provisional → measured) and verify they cite `docs/results/player-tracking.md`

## Workflow follow-up

- Validate with `openspec validate add-player-tracking --strict`, verify, then archive.
