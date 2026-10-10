# Tasks

## 1. Measure the capstone models

- [x] 1.1 Copy the action and jersey weights into `models/` (`action_yolo11m.pt`, `jersey_digits_yolov8m.pt`) and record their source runs in `docs/results/actions.md`
- [x] 1.2 Write `scripts/eval_actions.py` (download the test split, `model.val`) and record per-class and overall mAP@0.5 and split size
- [x] 1.3 Measure the capstone jersey model: found unusable (classes merged by index; horizontal flips), recorded in `docs/results/actions.md`
- [x] 1.4 Write `scripts/build_jersey_dataset.py` (classes by name, split by match, other-sport digits in train only) and verify tests; zip on Drive
- [ ] 1.5 Train `notebooks/train_jersey_digits.ipynb` on Colab and record test digit mAP per digit
- [ ] 1.6 Write `scripts/eval_jersey.py`: whole-number accuracy on the test crops by composing digits (and on jersey-detection-v3 if downloaded) and record it

## 2. `vball.actions` and `vball.jersey`

- [x] 2.1 Implement assignment of action boxes to tracks and merging into events; verify tests for the spike scenario, a box without a player and the confidence threshold
- [x] 2.2 Implement digit composition and the per-track vote; verify tests for two-digit numbers, an unclear vote and too few readings

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
