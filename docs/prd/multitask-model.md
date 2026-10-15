# PRD: Labelling loop and multi-task model

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-labelling-loop/`, `openspec/changes/add-multitask-model/`

## Problem
The analysis runs separate models per task (court keypoints v2/v3b, player detector, ball detector, action
classifier), each trained on a different public dataset. None of them was trained on the footage our users record:
a phone on a tripod at a court corner, low and wide, in Taiwanese amateur halls. The owner is willing to label such
footage over time. Labelling from scratch is slow (a full tracking label takes 1-2 hours per 30 s of video);
correcting the system's own output is several times faster and turns every review into training data.

One network with a shared backbone and one head per task can learn from all datasets at once, even though each image
is labelled for only some tasks, and runs faster than four models.

## User stories
- As the owner, I correct what the system got wrong in the review app (court points, ball, player boxes and ids,
  actions, rally winner), and each correction is saved as a label.
- As the owner, I see how many labels each task has and how the model improved after each retraining.
- As a coach, analysis gets better on my hall's footage as more of it is corrected.

## Requirements
1. Labelling in the web app on sampled frames of an analysed video, starting from the pipeline's output; a frame may
   be labelled for any subset of tasks; labels are versioned and exported in one dataset format.
2. A dataset builder merges our labels with the public datasets (SportsMOT, k6y7r, VNL, WASB data, Volleyball dataset)
   and splits by video or match, never by frame.
3. A multi-task network: shared backbone, heads for players (boxes), court keypoints (14 points), ball (position,
   from several consecutive frames) and, later, per-player action, re-identification embedding and rally winner;
   losses masked for tasks a sample has no label for. Training on Kaggle or Colab.
4. Each head replaces the current single-task model only when it is at least as good on that task's held-out test
   and on held-out labelled amateur footage; otherwise the single-task model stays.
5. Inference on a laptop CPU no slower than the current models together.

## Targets
Phase 1 (labelling loop): 5 amateur videos with court points and 200 corrected frames. Phase 2 (model): every head
within the adoption rule, total CPU time per frame lower than today.

## Risks
The ball is small and needs several frames; a shared single-frame backbone may lose to WASB. The first model will
likely be worse than the single-task models until enough amateur labels exist.
