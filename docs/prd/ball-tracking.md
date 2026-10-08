# PRD: Ball tracking

Parent: [README.md](README.md) · OpenSpec: `openspec/specs/ball-tracking/` (current behaviour); the improvement change opens at M4

## Current state
- VballNet V4c (ONNX, real time on CPU): about 3x fewer false jumps than the capstone's FastV1, continuous arcs.
- Weakness: on the wide high-angle men's broadcast only 28% of frames are detected; the ball is a few pixels in the 288×512 input.
- All current numbers are label-free proxies (detection rate, jump count), not accuracy.

## User stories
- As a coach, I see each point's full ball path so I can read the play.
- As a researcher, I know the tracker's real F1 on my own gym footage.

## Requirements
1. Per frame: whether the ball is seen and its image position. Missing frames are marked missing, never filled with fake values; interpolated values are flagged separately.
2. The model is swappable (V4c, FastV1, later TrackNetV5) without changing the output format.
3. Changing the model reruns from the ball stage only; court results are reused.

## Improvement plan (M4, in order, each measured by F1)
1. Higher input resolution, or overlapping tiles detected separately.
2. Compare TrackNetV5 (Yu-Shuen Wang's lab) and BlurBall.
3. Physical plausibility checks in court coordinates (the ball does not jump 5 m between frames).

## Acceptance criteria
- Own gym footage, ≥ 500 hand-labelled frames: F1 ≥ 0.85.
- Detection on the high-angle men's clip improves on 28%, reported with F1.

## Open questions
- Labelling tool: reuse the upstream VballNet label format or build a small labelling page (decided at M5).
