# Volleyball Analysis

Turning one camera's volleyball match recording into a reviewable record: ball path, court
coordinates, rallies and the score. Continuation of the NTOU senior capstone
"Volleyball Match Analysis System Based on Deep Learning"; work in progress.

This repository holds the analysis package (`vball`), the training and evaluation scripts, and the
planning documents. The web app is
[volleyball_analysis_webapp](https://github.com/DL-Volleyball-Analysis/volleyball_analysis_webapp)
(branch `redesign`), the public page is
[volleyvision-website](https://github.com/DL-Volleyball-Analysis/volleyvision-website).

## Status
| Component | State | Evidence |
|---|---|---|
| Ball tracking | VballNet V4c: 2.7× fewer false jumps than the capstone's FastV1 on 5 broadcast clips (proxy, no labels). Weak on wide high-angle shots (~28% detection). | [docs/results/ball-tracking.md](docs/results/ball-tracking.md) |
| Court registration | 14-point keypoint model (court lines + net band). v2: 0.49 m median error on held-out k6y7r images (target 0.3 m); v3 (bigger model, VNL data) training. | [docs/results/court-keypoints.md](docs/results/court-keypoints.md) |
| Player tracking | Planned: pretrained YOLO26 + BoT-SORT / ByteTrack, measured on SportsMOT volleyball first. | [openspec/changes/add-player-tracking](openspec/changes/add-player-tracking) |
| 3D trajectory | Planned: camera calibration from court + net keypoints, ballistic fit per flight. | [openspec/changes/add-ball-trajectory-3d](openspec/changes/add-ball-trajectory-3d) |
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
  scoring.py          rally winners -> running score (indoor set rules)
  metrics.py          ball-track metrics (label-free proxies + labelled F1)
scripts/            entry points (dataset build, evaluation, comparisons)
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
.venv/bin/python -m pytest tests
```

## Data and licences
- Code: MIT.
- VballNet models: asigatchov/fast-volleyball-tracking-inference (MIT).
- Court keypoint data: Roboflow Universe volleyball court keypoint sets (CC BY 4.0).
- SportsMOT (player tracking evaluation): CC BY-NC 4.0, research use only, not redistributed.

## Team
NTOU Department of Computer Science and Engineering capstone: Liang Yu-Jia (lead), Tsai Pei-Ying,
Chung Chia-Hsin; advisor Professor Ting Pei-Yi. Current rebuild by Liang Yu-Jia.
