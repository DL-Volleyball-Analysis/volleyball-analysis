# Tasks

## 1. Ball
- [x] 1.1 `vball.ball_detect` (VballNet whole frame / tiles, RAVEL-VB 011 / 012) and `vball.ball_track` (fixed objects, linking, gaps) with unit tests
- [x] 1.2 `scripts/eval_ball_detection.py` and `notebooks/eval_ball_volleyball.ipynb`; smoke run on a fake dataset in the same layout
- [ ] 1.3 Run on Kaggle; record the ablation and the WASB reference in `docs/results/ball-tracking.md`
- [ ] 1.4 If a method beats the current one on F1, make it the pipeline's ball method (stage version bump) and re-render the evaluation clips

## 2. Actors
- [x] 2.1 `vball.actors` (per-player scores, frame combination, ball prior) with unit tests
- [x] 2.2 `scripts/eval_actions_volleyball.py` and `notebooks/eval_actions_volleyball.ipynb`; smoke run of the scoring on the real labels
- [ ] 2.3 Run detection on Kaggle, score locally (validation-tuned, test-reported) with labelled and detected balls; record in `docs/results/actions.md`
- [ ] 2.4 If the ball prior improves test macro F1, use it in the actions stage with the pipeline's ball track (stage version bump)

## 3. Docs
- [ ] 3.1 README status, papers (method, ablations, references) and `openspec validate measure-ball-and-actors --strict`
