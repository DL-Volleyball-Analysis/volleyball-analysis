# Tasks

## 1. Line evidence
- [ ] 1.1 `vball.court_lines`: ridge map, line sampling, support score; unit tests on synthetic court images
- [ ] 1.2 Support of labelled fits on k6y7r test and VNL held-out (ROC AUC for error < 0.5 m); threshold from training images

## 2. Refinement
- [ ] 2.1 Homography refinement maximising support with the keypoint penalty; tests on shifted synthetic courts
- [ ] 2.2 Error before / after refinement on the labelled test sets

## 3. Pipeline
- [ ] 3.1 Court registration status from line support + fit error (court stage version bump); net check kept for calibration
- [ ] 3.2 Rerun the nine videos; overlays reviewed; results in docs/results/court-keypoints.md

## 4. Phase 2 (only if low end-line views stay unsolved)
- [ ] 4.1 Perspective augmentation for low camera angles in court keypoint training (Kaggle); evaluation as above
