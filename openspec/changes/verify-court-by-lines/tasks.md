# Tasks

## 1. Line fit
- [x] 1.1 `vball.court_lines`: background plate, line pixels (bright and dark), line candidates, court fit with checks and score; tests on synthetic courts (side and end-line views, a fan rejected, dark lines)
- [ ] 1.2 Fit on the six fixed clips and five broadcast clips; overlays checked

## 2. Pipeline
- [x] 2.1 Court registration: still shots compare the line fit with the keypoint fit, status from line evidence (court stage version bump); tests
- [ ] 2.2 Rerun the fixed and broadcast clips; court, players, 3D before / after

## 3. Evaluation
- [ ] 3.1 One labelled frame per fixed clip; error in court metres; results in docs/results/court-keypoints.md

## 4. Phase 2 (only if needed)
- [ ] 4.1 Moving cameras: line fit per sampled frame with players masked
- [ ] 4.2 Perspective augmentation for low and end-line views in keypoint training (Kaggle)
