# Proposal

## Why

Player tracks break at crossings, group blocks, exits from the frame and every pause between rallies: IDF1 0.690 with
411 identity switches on SportsMOT volleyball validation. A new id per break splits statistics, the tactics board and
the toucher that 3D anchors and actions rely on. BoT-SORT matches by position and motion only. Re-identification adds
appearance: an embedding per player crop, compared when tracks are associated and when broken tracks are joined.

## What Changes

- Evaluation: the tracking evaluation gains switches for appearance matching and track joining, and reports IDF1,
  HOTA, MOTA and identity switches per variant on the SportsMOT volleyball validation sequences, with time per frame.
- Step 1, no training: BoT-SORT with `with_reid` on, appearance from the detector's own features.
- Step 2, only if step 1 misses the target: a re-identification embedding trained on SportsMOT volleyball training
  crops (Kaggle or Colab), listed in `models/manifest.json`, used by the tracker.
- Step 3: `vball.reid` joins non-overlapping tracks after tracking by appearance, plausible court movement, side, team
  and shirt number, keeping at most twelve players on court.
- Players stage version bumps only for the steps that are adopted; a step is adopted when it raises IDF1 without
  lowering HOTA.

## Impact

- Specs: player-tracking (identity across gaps; measured re-identification).
- Code: `vball.reid` (new), players stage, `vball.evaluation` tracking evaluation, tracker configuration.
- Models: possibly one new weight file (step 2).
- Not included: a multi-task network (see the PRD, out of scope).
