# Analysis speed

Change speed-up-analysis (PRD docs/prd/analysis-speed.md). Stage times on fixed_hawaii_irvine (3 min, 1280x720,
29 fps, four camera shots, all still), on the development laptop (Apple silicon, CPU), measured by the stage progress
callbacks of `pipeline.run`:

| Stage | Before (s) | After (s) | Change |
|---|---|---|---|
| decode | - | 18 | |
| court | 364 | 98 | 1 keypoint sample per second in still shots instead of 5 |
| ball | 62 | 67 | |
| players | 183 | 190 | |
| actions | 286 | 313 | |
| trajectory (3D) | 105 | 23 | one calibration per still shot |
| rallies | 337 | 375 | quick check passed (see below), full cue pass as before |
| **total** | **1404** | **1142** | |

Results unchanged: four shots ok from line evidence, players placed, 68 flights (34 rejected) before and after.

The target (court, 3D and rallies together 3x faster) is **not met**: 806 -> 496 s (1.6x). The rallies quick check
does not stop this clip: the old court keypoint model fits a plausible (but wrong) court in 69% of the checked frames
and the player detector sees about 10 people, so the clip looks like training footage and the full cue pass runs
(it then finds 5 rallies where the score bug shows 14 points; docs/prd/score-labels.md). The rallies stage only gets
cheap once its cues come from the earlier stages' results (change label-rallies-from-score, task 2.1). Ball,
players and actions were not touched by this change; small differences are run-to-run noise with another job running.
