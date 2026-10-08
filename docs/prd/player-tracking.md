# PRD: Player detection and tracking

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-player-tracking/`

## Problem
The analysis has no player detection today. The capstone used YOLOv8 + Norfair, but its accuracy was never measured on labelled data, and it was removed with the old pipeline. Several goals depend on knowing where the players are: the 2D tactics board, who attacked (attack efficiency), and touches for rally logic.

## User stories
- As a coach, I see where every player on court stood during a rally, on a top-down court.
- As a coach, I can tell the two sides apart, so positions and later statistics belong to the right team.
- As a researcher, I know the tracker's real accuracy on labelled volleyball footage before trusting any statistic built on it.

## Requirements
1. Detect the players on court in each analysed frame (box in image pixels, confidence).
2. Track them so each player keeps one id through a rally.
3. Keep only on-court players: referees, line judges, bench and audience are excluded, using the court mapping (feet inside the court plus free zone).
4. Give each player a court position in metres (feet point mapped through the court mapping) and a side of the net.
5. Report accuracy with standard tracking metrics (HOTA, IDF1, MOTA, detection recall/precision) on labelled data, separately from any unlabelled proxy.
6. Without a court mapping, still detect and track, but mark positions and on-court filtering as unavailable rather than guessing.

## Approach (measure before training)
1. **Baseline with a pretrained model:** YOLO26 person detection (COCO) + ultralytics' built-in tracker (BoT-SORT / ByteTrack). No training.
2. **Measure** on labelled volleyball sequences: SportsMOT volleyball split (MCG-NJU, ICCV 2023; CC BY-NC 4.0, research use only) and our own labelled gym clips (M5).
3. **Train only if needed:** fine-tune the detector on SportsMOT volleyball training sequences on Colab when the baseline misses the targets below.

## Acceptance criteria (provisional, revisited after the baseline is measured)
- SportsMOT volleyball validation: IDF1 ≥ 0.70 and detection recall ≥ 0.95 for on-court players.
- Own gym footage: ≤ 1 non-player kept per 100 frames after on-court filtering.
- Throughput on the M1 Pro CPU: a 2-hour match analysed in ≤ 1 hour for this stage (detection at a reduced frame rate is acceptable).

## Out of scope
- Player identity across rallies and jersey numbers (separate change; the capstone OCR has no accuracy data).
- Pose and action recognition (spike, set, receive).
- Multi-camera tracking.

## Dependencies
- Court mapping (court-registration) for filtering and positions; detection and tracking alone do not need it.
- SportsMOT access (official download may require registration).

## Open questions
- Detection frame rate (every frame vs 10 fps with interpolation) is decided by the measured CPU time; it does not change the requirements.
