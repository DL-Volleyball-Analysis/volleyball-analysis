# Tasks

## 1. Data
- [ ] 1.1 Inspect the orel and Volleylitics formats; record clip and frame counts per source and split in docs/results/ball-tracking.md
- [ ] 1.2 `scripts/build_ball_clips.py` with tests (formats, splits by match, letterbox labels)

## 2. Training
- [ ] 2.1 `training/ball/train_wasb.py` (dataset, focal / QFL loss, checkpoints, resume) with a 1-step local smoke test
- [ ] 2.2 Kaggle notebook; train mixes 2 and 3

## 3. Evaluation and pipeline
- [ ] 3.1 Evaluate WASB weights and both mixes on the broadcast test and gym held-out matches; contact sheets on our clips
- [ ] 3.2 If a model wins on both, make it the pipeline's ball model (stage version bump); re-measure 3D and actions
- [ ] 3.3 README, papers, `openspec validate train-ball-detector --strict`
