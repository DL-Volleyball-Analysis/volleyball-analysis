# DL-Volleyball-Analysis: repository organisation

State on 2026-10-10. Reorganised 2026-10-08; on 2026-10-10 the archived repositories were tidied (concise README with
corrected results, weights and videos removed from the latest version, description and topics) and renamed with a
`capstone-` prefix. GitHub redirects the old names.

## Active repositories

| Repo | Role |
|---|---|
| `volleyball-analysis` | everything that is code: the `vball` package, the web app (`webapp/`), capstone training code (`training/`), notebooks, scripts, PRD, OpenSpec, results |
| `volleyvision-website` | public landing page (GitHub Pages; the URL follows the repository name) |
| `capstone-report` | the graded LaTeX report; graded version tagged `capstone-final`, unsupported numbers removed after it |
| `.github` | organisation profile (GitHub requires this name) |

## Archived (read-only, history kept)

| Repo (old name) | Now in | Note |
|---|---|---|
| `capstone-webapp` (`volleyball_analysis_webapp`) | `volleyball-analysis/webapp/` | files of the `redesign` branch copied without history: the old history holds ~400 MB of weights and a database |
| `capstone-action-recognition` (`action-recognition-yolov11`) | `volleyball-analysis/training/action-recognition/` | `yolo11m.pt` base model not copied (Ultralytics downloads it) |
| `capstone-jersey-numbers` (`jersey-number-detection`) | `volleyball-analysis/training/jersey-numbers/` | training log kept in `results/`; plots stay in the archived repo |
| `capstone-prototype` (`volleyball-prototype`) | superseded | early prototype |
| `capstone-court-detection` (`volleyball-court-detection`) | superseded by `vball` court registration | manual 4-click court, pixel thresholds |

Each archived repository's README starts with a note pointing here; removed weights stay in its history.

## Conventions
- No model weights, datasets, videos or training outputs in git (`*.pt`, `*.onnx`, `data/`, `runs/` are ignored).
- One CI workflow at the root: package tests, web app backend tests, frontend lint, tests and build.
- Kebab-case names for new repositories and folders; `capstone-` prefix for the capstone-era archives.
