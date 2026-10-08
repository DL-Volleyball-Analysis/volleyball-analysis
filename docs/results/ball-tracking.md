# Ball tracking: results

## VballNet V4c vs FastV1 (2026-10-07, `scripts/compare_ball_models.py`)
Five short 1080p broadcast clips (1,398 frames in total). **No labels: these are proxies**, not accuracy.
"Detection rate" is the share of frames with a detection; "jumps" are consecutive detections farther
apart than 8% of the frame width (a false detection or a lost track).

| Clip | Frames | FastV1 detection | V4c detection | FastV1 jumps / 100 frames | V4c jumps / 100 frames |
|---|---|---|---|---|---|
| broadcast_back_rally | 226 | 0.717 | 0.735 | 8.64 | 5.42 |
| broadcast_back_view | 420 | 0.655 | 0.738 | 4.73 | 1.94 |
| broadcast_side_high_men | 153 | 0.294 | 0.281 | 20.00 | 6.98 |
| broadcast_side_high_women | 178 | 0.708 | 0.669 | 18.25 | 6.72 |
| broadcast_side_rally | 421 | 0.618 | 0.767 | 3.46 | 0.00 |
| **All (frame-weighted)** | 1,398 | 0.621 | 0.687 | 8.37 | 3.08 |

V4c has 2.7× fewer jumps overall. Both models fail on the wide high-angle men's clip (~28% of frames),
where the ball is a few pixels in the 288 × 512 input.

## Published benchmark (not measured here)
VballNet V4c: F1 0.902, precision 0.900, recall 0.904, 149.6 FPS inference-only on CPU, on the
authors' test set ([fast-volleyball-tracking-inference](https://github.com/asigatchov/fast-volleyball-tracking-inference)).

## Not measured yet
F1 on our own labelled gym footage (PRD ball-tracking acceptance criterion).
