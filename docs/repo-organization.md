# DL-Volleyball-Analysis: repository organisation plan

Status: proposal, 2026-10-08. Nothing here has been pushed. Every action marked **needs OK** changes a shared repository and waits for the owner (and, where noted, the teammates).

## 1. Current state (surveyed 2026-10-08)

| Repo | Size (HEAD) | What it is | Problems |
|---|---|---|---|
| `volleyball_analysis_webapp` | 194 MB | capstone web app; rewritten on local branch `redesign` | 185 MB of `.pt` weights committed; name uses `_` while all others use `-` |
| `volleyvision-website` | 93 MB | Next.js landing page on GitHub Pages | 40 unused source files, 30 unused packages, two deploy workflows (double deploy), 66 MB `demo.mov` duplicating a 4 MB `demo.mp4`; claims "98.5% detection accuracy" and "automatic court detection" that were never measured / built |
| `volleyball-prototype` | 464 MB | early prototype scripts | duplicated model weights (DaSiamRPN, YOLO v7/v8/v11); superseded |
| `capstone-report` | 78 MB | LaTeX report, EN + ZH | built PDFs (49 MB) committed next to sources |
| `volleyball-court-detection` | 9 MB | landing + in/out with manual 4-click court and pixel thresholds | superseded by `vball` court registration; ONNX models committed |
| `action-recognition-yolov11` | 41 MB | YOLOv11 action training script | commits `yolo11m.pt`, the public base model ultralytics downloads itself |
| `jersey-number-detection` | 6 MB | jersey number training | commits `runs/` training outputs |
| `.github` | 10 MB | organisation profile README | 1-2 MB PNG screenshots; content describes the capstone system |

Across all repos: no repository description or topics, no shared README layout, model weights in git history.

## 2. Target structure

| Repo | Role | Action |
|---|---|---|
| `volleyball-analysis` (new, this project) | core analysis package `vball`, research scripts, PRD, OpenSpec | **needs OK**: publish to the org (it is local-only today) |
| `volleyball-analysis-webapp` | product: API, worker, React UI | merge `redesign` into `main`; **needs OK** rename (GitHub keeps redirects from the old name) |
| `volleyvision-website` | public landing page | merge `cleanup`, then the content refresh (`openspec/changes/refresh-landing-page`) |
| `capstone-report` | the graded report | keep sources; move the PDFs to a GitHub Release; archive (read-only) |
| `volleyball-court-detection` | historical | README pointer to `vball` court registration; archive |
| `volleyball-prototype` | historical | README pointer; archive |
| `action-recognition-yolov11` | optional player features (teammate work) | delete `yolo11m.pt`, document download; keep active until the player-feature decision (PRD §7 Q2) |
| `jersey-number-detection` | optional player features (teammate work) | delete `runs/`, add it to `.gitignore`; same as above |
| `.github` | org profile | rewrite for the new system; compress screenshots |

Archiving keeps every repo, its history and the teammates' credit; it only makes it read-only and marks it as historical.

## 3. Conventions for every active repo
- Description and topics set (e.g. `volleyball`, `computer-vision`, `sports-analytics`).
- README sections: what it is · status · run · test · license · related repos.
- No model weights, datasets, videos or training outputs in git: weights go to GitHub Releases (or Hugging Face) and are fetched by a script; `.gitignore` covers `*.pt`, `*.onnx`, `runs/`, `data/`.
- Kebab-case repository names.
- CI builds and tests on every pull request.

## 4. History size (separate decision)
Deleting large files from the current commit does **not** shrink a clone: they stay in history. Shrinking needs a history rewrite (`git filter-repo`) and a force push, which breaks every existing clone and fork. **Needs OK from the owner and both teammates.** Recommended only for `volleyball-prototype` (464 MB) and `volleyball_analysis_webapp` (194 MB), and only after weights are published as Releases.

## 5. Done locally so far
- `volleyball_analysis_webapp`, branch `redesign`: capstone backend, Celery/Docker setup, old tests, committed DB and `models/` removed; new backend with tests.
- `volleyvision-website`, branch `cleanup`: 40 unreferenced source files and 30 unused packages removed, duplicate `nextjs.yml` workflow removed, hero video switched from `demo.mov` (66 MB) to the identical `demo.mp4` (4 MB, checked frame by frame); `npm run build` passes.

## 6. Order of execution
1. Owner reviews this plan and the two local branches.
2. Push branches and open pull requests in the org (**needs OK**).
3. Descriptions, topics, READMEs, `.gitignore` for all repos (**needs OK**, low risk).
4. Publish weights as Releases; delete them from HEAD.
5. Archive the historical repos (**needs OK**).
6. Optional history rewrite (**needs OK** from the whole team).
