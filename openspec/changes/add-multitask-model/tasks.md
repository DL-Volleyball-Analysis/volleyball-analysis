# Tasks

## 1. Data
- [ ] 1.1 Public datasets converted by `vball.datasets.labels` (needs add-labelling-loop 3.1); per-task counts

## 2. Model
- [ ] 2.1 Network: shared backbone, player, court and three-frame ball heads; masked loss; unit tests on tiny inputs
- [ ] 2.2 Notebook for Kaggle/Colab; first training run

## 3. Evaluate and adopt
- [ ] 3.1 Each head against its single-task model on the existing tests and the amateur test videos; CPU time
- [ ] 3.2 Multi-task adapter in vball.pipeline.models for adopted heads; stage version bumps; golden check
- [ ] 3.3 Results recorded in docs/results/multitask.md (also heads that lost)

## 4. Later heads
- [ ] 4.1 Action per player, re-identification embedding, rally winner, each with the same adoption rule
