# Tasks

## 1. Core
- [x] 1.1 `vball.rallies`: CVAT label parsing, hysteresis segmentation, IoU matching and boundary errors, with unit tests
- [x] 1.2 `scripts/eval_rallies.py`: train on train matches, choose segmentation on validation, report on test

## 2. Cues
- [x] 2.1 `scripts/extract_rally_cues.py` (court, ball, players at 5 per second) and a Kaggle notebook for the 8 matches
- [x] 2.2 Ball-rule baseline and the classifier; results in `docs/results/rallies.md`
- [ ] 2.3 VideoMAE checkpoint as a reference if its training split allows a fair test

## 3. Pipeline
- [ ] 3.1 Rallies stage from the detector (stage version bump), demo data only when no result; API and UI unchanged
- [ ] 3.2 README, papers, `openspec validate add-rally-detection --strict`
