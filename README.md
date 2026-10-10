# Volleyball Analysis

Turning one camera's volleyball match recording into a reviewable record: ball path, court
coordinates, rallies and the score. Continuation of the NTOU senior capstone
"Volleyball Match Analysis System Based on Deep Learning"; work in progress.

This repository holds the analysis package (`vball`), the web app (`webapp/`), the training and
evaluation scripts, and the planning documents. The public page is
[volleyvision-website](https://github.com/DL-Volleyball-Analysis/volleyvision-website).

## Status
| Component | State | Evidence |
|---|---|---|
| Ball tracking | VballNet V4c: 2.7× fewer false jumps than the capstone's FastV1 on 5 broadcast clips (proxy, no labels). Weak on wide high-angle shots (~28% detection). | [docs/results/ball-tracking.md](docs/results/ball-tracking.md) |
| Court registration | 14-point keypoint model, per-shot registration in the pipeline with a floor-net consistency check. v2: 0.49 m on held-out images; v3 interim 0.17 m on held-out broadcast clips but 7.91 m on gym images (box convention bug, v3b training). | [docs/results/court-keypoints.md](docs/results/court-keypoints.md) |
| Player tracking | YOLO26s + BoT-SORT at 10 fps in the pipeline, with on-court filtering: IDF1 0.484 on SportsMOT volleyball (target 0.70); 39% of boxes are people off court. | [docs/results/player-tracking.md](docs/results/player-tracking.md) |
| 3D trajectory | Calibration, ballistic fit, the trajectory stage and the 2D / 3D tactics board are built; 0.05 m median error on a synthetic serve, spikes flagged low quality. Real footage waits for court model v3 (v2 calibrates 4 / 49 test views). | [docs/results/trajectory.md](docs/results/trajectory.md) |
| Player statistics | Attack and serve tags in the review app; attack efficiency, kill rate, aces and serve errors per player and set, CSV export (phase 1: coach tags). | [docs/prd/player-stats.md](docs/prd/player-stats.md) |
| Landing / scoring | Scoring rules implemented (`vball.scoring`); rally detection planned. | [docs/prd/rally-scoring.md](docs/prd/rally-scoring.md) |
| Action recognition (capstone) | YOLOv11m mAP@0.5 0.945 on the validation split. | [docs/results/action-recognition.md](docs/results/action-recognition.md) |

Every number comes from a script and a labelled split, or is named a proxy or a published
benchmark. A metric without labelled data is reported as "not measured".

## How the work is planned
- [docs/prd/](docs/prd/README.md): product requirements — why, for whom, what counts as success.
- [openspec/specs/](openspec/specs): how the system behaves today (behaviour contracts).
- [openspec/changes/](openspec/changes): each change's proposal, spec deltas, design and task list.
- [docs/results/](docs/results): measurements behind every number.

## Layout
```
src/vball/          analysis package
  paths.py            project locations and model registry
  ball.py             VballNet ONNX ball tracking (wraps the upstream inference script)
  court.py            court model (18 x 9 m) and homography helpers
  court_geometry.py   geometric court registration (experimental fallback)
  court_keypoints.py  14-point court keypoint layout, flip index, label completion
  players.py          player detection + tracking with interpolation
  calibration.py      camera focal length and pose from court + net keypoints
  trajectory/         flights between touches, ballistic 3D fit, synthetic rallies
  scoring.py          rally winners -> running score (indoor set rules)
  stats.py            attack / serve tags -> outcomes and player statistics
  metrics.py          ball-track metrics (label-free proxies + labelled F1)
scripts/            entry points (dataset build, evaluation, comparisons)
webapp/             web app: FastAPI API + worker (backend/), React UI (frontend/); see webapp/README.md
training/           capstone training code: action recognition, jersey numbers
notebooks/          Colab training notebooks (GPU work runs on Colab)
tests/              pytest
docs/               PRD, results, design notes
openspec/           specifications and changes
models/ data/ outputs/ external/   not in git (weights, datasets, results, third-party repos)
```

## Setup
```
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -e .
```
Ball tracking needs [fast-volleyball-tracking-inference](https://github.com/asigatchov/fast-volleyball-tracking-inference)
(MIT) cloned into `external/`; player-tracking evaluation needs
[TrackEval](https://github.com/JonathonLuiten/TrackEval) (MIT) there too.

## Run
```
.venv/bin/python scripts/compare_ball_models.py                     # ball model comparison
.venv/bin/python scripts/download_datasets.py                       # court keypoint data (ROBOFLOW_API_KEY)
.venv/bin/python scripts/inspect_court_keypoints.py data/datasets/<set>
.venv/bin/python scripts/build_court_dataset.py --no-drive          # dataset zip for Colab
.venv/bin/python scripts/eval_player_tracking.py --gt-as-tracker    # tracking evaluation sanity check
.venv/bin/python scripts/eval_trajectory_synthetic.py              # 3D fit on synthetic rallies
.venv/bin/python -m pytest tests                                    # web app: see webapp/README.md
```

## Data and licences
- Code: MIT.
- VballNet models: asigatchov/fast-volleyball-tracking-inference (MIT).
- Court keypoint data: Roboflow Universe volleyball court keypoint sets (CC BY 4.0).
- SportsMOT (player tracking evaluation): CC BY-NC 4.0, research use only, not redistributed.

## Team
NTOU Department of Computer Science and Engineering capstone: Liang Yu-Jia (lead), Tsai Pei-Ying,
Chung Chia-Hsin; advisor Professor Ting Pei-Yi. Current rebuild by Liang Yu-Jia.
