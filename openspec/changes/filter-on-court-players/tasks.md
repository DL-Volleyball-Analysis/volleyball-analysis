# Tasks

## 1. Player-only detector

- [x] 1.1 Write `scripts/build_sportsmot_detection.py` (15 train sequences, every 3rd frame, one class, split by sequence) and verify tests for the label conversion
- [x] 1.2 Write `notebooks/train_player_detector.ipynb` (Colab / Kaggle); verify a local smoke run of the converter (done 2026-10-11; instead of a private Kaggle dataset the notebook streams the 15 sequences from Hugging Face, so nothing is re-uploaded)
- [ ] 1.3 Train on Kaggle; evaluate with `scripts/eval_player_tracking.py` on the 15 val sequences; record against the baseline and install only if IDF1 and precision both improve

## 2. Cap and role

- [x] 2.1 Cap at 12 players per frame in `vball.players` and verify tests (placed first, then confidence)
- [x] 2.2 Implement `vball.teams` (torso colour histograms, k = 2, outliers as `other`, on-court override) and verify tests with synthetic coloured boxes
- [x] 2.3 Measure the role check on SportsMOT val (non-player tracks caught, players wrongly marked) and record it

## 3. Web app

- [x] 3.1 Players stage writes `role` and `team`; court positions, actions and statistics use players only; bump the stage version and verify backend tests
- [ ] 3.2 Overlay and render.py show `other` dimmed; verify component tests and re-render the five clips (no boxes on the first referee and line judges, by eye) (2026-10-11: code and tests done, re-rendered; by eye not met yet: a line judge and bench members still labelled, two back-row players dimmed on the clip without a court; waits for task 1)

## 4. Docs

- [ ] 4.1 Update `docs/results/player-tracking.md`, README status and the web app README; `openspec validate filter-on-court-players --strict`
