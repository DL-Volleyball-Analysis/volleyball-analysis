# Analysis speed: a full match analysed in reasonable time

Version 1.0 · 2026-10-12 · Owner: YuJia Liang · Parent: [README.md](README.md)

## Why
A 3-minute fixed-camera clip takes 23-26 minutes to analyse on the development laptop (Apple silicon, CPU), so a
90-minute match would take over 12 hours. Stage times on fixed_hawaii_irvine (3 min, 29 fps): court 364 s, rallies
337 s, actions 286 s, players 183 s, 3D 105 s, ball 62 s. Three of these repeat work:

| Stage | Repeated work |
|---|---|
| Court | two keypoint models on 5 samples per second, also in shots where the camera never moves and line evidence decides |
| 3D | a camera calibration per flight, also when every flight of a shot has the same still camera |
| Rallies | court, player and ball detection over the whole video again, only to report that the footage is out of training |

## What
1. Still shots: keypoint samples at 1 per second.
2. Still shots: one camera calibration for all their flights.
3. Rallies: a quick check on a few frames first; footage outside the model's training is reported at once.
4. Later (change after this one): rally cues from the earlier stages' results instead of a second detection pass, and
   the rally model retrained on them.

## Success
- fixed_hawaii_irvine: court, 3D and rallies stages together at least 3x faster, with the same court status and
  sources, the same number of calibrated shots, and rallies reported the same way.
- No change on broadcast clips with a moving camera.
