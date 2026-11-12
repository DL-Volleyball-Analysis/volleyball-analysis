# Visual check of the demo clip (2026-11-12)

`fixed_hawaii_pennstate` (NCAA, fixed end-line camera, 3 min, results as in the app). For each of the 16 detected
rallies, frames at 25%, 50% and 75% of its span (48 frames) were drawn with the system's court lines, player boxes and
ball position and checked **by eye**, ball marks on 240 px crops at full resolution. This is a qualitative check, not
an accuracy measure: no frame was labelled. Sheets and per-frame judgements: `outputs/visual_check/fixed_hawaii_pennstate/`
(script `sheets.py`, `ball_crops.py` there).

| Output | Result by eye |
|---|---|
| Court lines | aligned with the painted lines in 48 of 48 frames (consistent with the labelled 0.02-0.06 m) |
| Players | every on-court player boxed in every frame; line judges and an advertising board in the near right corner are boxed too in most frames |
| Ball, frames with a mark (35) | on the ball 19, wrong 13, unsure 3 |
| Ball, frames without a mark (13) | not checked for misses one by one; at least one (S8-4) shows the ball on the floor while the mark is elsewhere |

**The wrong ball marks have one main cause:** 9 of 13 sit on a light, round, slowly moving object off court, the heads of
the referee and line judges (light or white hair) or their shoes; 2 on the score text, 2 in the crowd. The fixed-object
check (`vball.ball_track.drop_fixed`) removes static look-alikes but not officials who move a little. Fixes worth
measuring: drop ball candidates outside the court plus a margin when no player is near, and drop candidates inside the
score bug's box (`vball.scorebug` already finds it).

**Player false positives** are static: an advertising board and line judges standing at the corners. A track that does
not move over the whole video, or stands outside the court's free zone at a corner, can be dropped.

**Demo moments** where court, players and ball are all right on the sampled frames: rally 4 (31-34 s) and rally 8
(68-73 s).
