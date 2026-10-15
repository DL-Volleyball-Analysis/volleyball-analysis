# PRD: Player re-identification

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-player-reid/`

## Problem
Player tracks break. On the SportsMOT volleyball validation sequences the fine-tuned detector with BoT-SORT reaches
IDF1 0.690 with 411 identity switches (docs/results/player-tracking.md): players cross at the net, block in groups,
leave the frame and come back, and every pause between rallies ends their tracks. Each break gives a player a new id,
so statistics, the tactics board and the toucher used by 3D anchors and actions are split over several ids. The
tracker matches by position and motion only; it never asks whether two tracks look like the same person.

Teammates wear the same shirt, so generic pedestrian appearance (clothing colour) does not separate them; body shape,
hair, shoes and the shirt number do.

## User stories
- As a coach, a player keeps one id through a rally, including after crossing or blocking with teammates.
- As a coach, a player keeps the same id from one rally to the next, so per-player statistics add up.
- As a researcher, I know how much re-identification changes IDF1, HOTA and identity switches on labelled data.

## Requirements
1. Measure first: the current tracker with its built-in appearance matching switched on (BoT-SORT `with_reid`, using
   the detector's own features), no training, on the SportsMOT volleyball validation sequences.
2. If that is not enough, train a re-identification embedding on SportsMOT volleyball training crops (identities are
   per sequence) on Kaggle or Colab, and use it in the tracker.
3. Join broken tracks after tracking: tracks that never overlap in time are merged when their appearance is close, the
   jump in court position is plausible, they are on the same side and team, and the shirt number does not contradict;
   at most twelve players on court stays a hard limit.
4. Adopt a step only when it raises IDF1 on the validation sequences without lowering HOTA; report every step, also
   the ones that do not help.
5. Keep running on a laptop CPU: report the added time per frame.

## Targets
IDF1 ≥ 0.75 and fewer identity switches than 411 on SportsMOT volleyball validation, at ≤ 30% more time per frame.

## Later
A re-identification head on the multi-task network (multitask-model.md) once that network exists; the trained
embedding here is its baseline.
