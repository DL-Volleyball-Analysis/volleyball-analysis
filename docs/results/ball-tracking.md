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

## Labelled evaluation: Volleyball dataset test split (2026-10-11)
`scripts/eval_ball_detection.py` via `notebooks/eval_ball_volleyball.ipynb` (Kaggle; change measure-ball-and-actors).
The Volleyball dataset (Ibrahim et al., CVPR 2016) with the ball position in every frame (Perez et al., Pattern
Recognition 2022): 16 test matches, 1,337 clips, 54,817 frames, a ball labelled in 92.3% of them (positions of an
occluded ball estimated by the annotators count as visible). A detection within tau pixels of the label is a true
positive; a farther one is both a false positive and a miss. None of these detectors was trained on this dataset.

| Method | P / R / F1 at 4 px | P / R / F1 at 10 px | Frames with a detection | ms / frame (T4) |
|---|---|---|---|---|
| VballNet V4c | 0.397 / 0.211 / 0.275 | 0.569 / 0.301 / 0.394 | 48.9% | 22 |
| V4c + tracker | 0.500 / 0.165 / 0.248 | 0.729 / 0.240 / 0.361 | | 24 |
| V4c on 2 x 2 tiles | 0.277 / 0.231 / 0.252 | 0.373 / 0.310 / 0.338 | 76.7% | 103 |
| tiles + tracker | 0.391 / 0.170 / 0.236 | 0.542 / 0.235 / 0.328 | | 105 |
| RAVEL-VB-011 | 0.455 / 0.190 / 0.268 | 0.749 / 0.313 / **0.441** | 38.5% | 17 |
| RAVEL-011 + tracker | 0.568 / 0.148 / 0.235 | **0.871** / 0.227 / 0.360 | 24.0% | 20 |
| RAVEL-VB-012 | 0.214 / 0.213 / 0.213 | 0.286 / 0.283 / 0.284 | 91.5% | 41 |
| RAVEL-012 + tracker | 0.398 / 0.170 / 0.238 | 0.543 / 0.232 / 0.325 | | 43 |

- **Not an evaluation error.** Predictions and labels share coordinates (median ratio 1.00 in x and y), and when a
  detector finds the ball it is accurate: median 4.3 px from the label for RAVEL-011.
- **The detectors do not transfer.** On these older 720p broadcasts they miss most balls (recall 0.2-0.3) and fire on
  other objects (V4c precision 0.40 at 4 px). For reference, WASB trained on this dataset reports F1 0.865 at 4 px.
- **The tracker trades recall for precision** (RAVEL-011 at 10 px: 0.749 -> 0.871 precision, 0.313 -> 0.227 recall),
  so F1 does not improve; its thresholds were set on our own clips and not tuned here.
- **Tiles do not help here**: more candidates, lower precision. They helped on our wide 1080p men's clip by eye, where the
  ball is smaller than in these 720p clips.
- Next: WASB's published Volleyball-dataset weights as a detector (`vball.ball_detect.Wasb`, ONNX export in
  `notebooks/eval_wasb_volleyball.ipynb`), measured with the same script.

### WASB with its published Volleyball-dataset weights (2026-10-12)
`notebooks/eval_wasb_volleyball.ipynb`: WASB's HRNet built with its own code, the published weights loaded and exported
to ONNX with the sigmoid included (`vball.ball_detect.Wasb`, windows of 3 frames, step 3), evaluated by the same script
and on the same test clips as the table above:

| Method | P / R / F1 at 4 px | P / R / F1 at 10 px |
|---|---|---|
| WASB (published weights) | 0.679 / 0.628 / **0.652** | 0.981 / 0.907 / **0.942** |
| WASB + tracker | 0.670 / 0.605 / 0.636 | 0.961 / 0.868 / 0.912 |

- In-domain training is what matters: F1 at 10 px 0.942 against 0.394 (V4c) and 0.441 (RAVEL-011) on these clips.
- WASB reports F1 0.865 at 4 px on this split; our 0.652 uses step-3 windows, our letterboxed input and a metric that
  counts a far detection as both a false positive and a miss. WASB's own evaluation is re-run with one GPU to compare
  like for like. (The notebook's first ONNX check reported a 0.48 difference: the comparison ran after the export had
  put the BatchNorm layers back in training mode; in eval mode ONNX and PyTorch agree to 4e-7, so the ONNX model and
  the numbers above are valid.)
- The tracker does not help a detector this precise: it removes some true detections with the false ones.
- On gym footage VballNet is strong (F1 0.859 at 10 px on the held-out orel matches) while WASB was trained on broadcast
  only: the mixed fine-tuning (`notebooks/train_ball_detector.ipynb`) tests one model for both.
