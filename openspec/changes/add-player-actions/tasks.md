# Tasks

## 1. Measure the capstone models

- [x] 1.1 Copy the action and jersey weights into `models/` (`action_yolo11m.pt`, `jersey_digits_yolov8m.pt`) and record their source runs in `docs/results/actions.md`
- [x] 1.2 Write `scripts/eval_actions.py` (download the test split, `model.val`) and record per-class and overall mAP@0.5 and split size
- [ ] 1.3 Write `scripts/eval_jersey.py` (digit mAP on the test split; whole-number accuracy by composing digits) and record both

## 2. `vball.actions` and `vball.jersey`

- [ ] 2.1 Implement assignment of action boxes to tracks and merging into events; verify tests for the spike scenario, a box without a player and the confidence threshold
- [ ] 2.2 Implement digit composition and the per-track vote; verify tests for two-digit numbers, an unclear vote and too few readings

## 3. Pipeline and API (web app)

- [ ] 3.1 Add the `actions` stage after `players` (unavailable without models, opt-in until task 1 is recorded) and verify backend tests with fake detectors
- [ ] 3.2 Add `GET /videos/{id}/actions` (events, numbers per track, suggestions) and verify API tests; regenerate frontend types

## 4. Display

- [ ] 4.1 Numbers on overlay boxes and the court map, `ID n` otherwise; verify component tests
- [ ] 4.2 Actions timeline lane; verify component tests
- [ ] 4.3 Numbers and action labels in `render.py`; render one evaluation clip and check numbers against the shirts by eye

## 5. Suggested tags

- [ ] 5.1 Show suggestions in the tag lane and inspector (accept / edit / dismiss); verify that accepting creates the same tag as typing and that suggestions never count in statistics

## 6. Docs

- [ ] 6.1 Update README status, PRD index, web app README; validate with `openspec validate add-player-actions --strict`
