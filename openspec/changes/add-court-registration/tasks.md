# Tasks

## 0. Court model v3 (data and model)

- [x] 0.1 Add front-zone completion to `vball.court_keypoints` (homography from 4 floor points → all floor points; calibration → net points, used for checks only) and verify on k6y7r labels: completed vs labelled points, median and p90 error in pixels recorded in `docs/results/court-keypoints.md`
- [x] 0.2 Build dataset v3 (k6y7r + VNL clips one-three completed, every 2nd frame; VNL four-five as `test_vnl`, boxes from completed points) and verify split counts and that no clip appears in two splits
- [x] 0.3 Notebook v3 (YOLO26s-pose, 1280 px, 400 epochs, run `court_kpt_v3`, Drive checkpoints and resume) and verify a 1-epoch local smoke run on the v3 zip
- [ ] 0.4 After Colab training, measure end-to-end metre error on k6y7r test and `test_vnl`, and net-point pixel error on k6y7r test (v2 vs v3 side by side), and record it in `docs/results/court-keypoints.md`


## 1. Keypoints to homography (`vball.court_keypoints`)

- [x] 1.1 Add `fit_homography(keypoints, image_size)` (floor points, confidence filter, RANSAC, normalised RMS error) and verify with tests that project the known court through a synthetic camera, add noise and outliers, and recover corners within 1 px
- [x] 1.2 Add the geometric sanity check (convex, label handedness, ≥ 2% image area) and verify tests reject mirrored, folded and tiny courts
- [x] 1.3 Add `detect(model, frame)` returning 14 × (x, y, conf) in original pixels and verify on a k6y7r test image that output shape and coordinate scale match the label file

## 1b. Line refinement

- [ ] 1b.1 Implement line refinement from a starting homography (edge search near projected lines, robust fit, bounds) and verify on synthetic images with a 1 m offset start: corners recovered within 0.1 m, and a start on an ad board is rejected
- [ ] 1b.2 Measure refinement on k6y7r test and `test_vnl` (end-to-end metres, with vs without) and record it

## 2. Per-shot registration (`vball.court_registration`)

- [x] 2.1 Implement sampling at a configurable rate within each shot and verify a test that sample frames never cross shot boundaries
- [x] 2.2 Implement per-corner running-median smoothing within a shot and verify a test where one outlier sample is removed and a steady pan is preserved
- [x] 2.3 Implement `mapping_at(court, frame)` by corner interpolation and verify a test that frames at samples reproduce the sample corners and midpoints lie between them
- [x] 2.4 Implement shot status (ok / needs_review / failed) from a single threshold config and verify tests for each status
- [x] 2.5 Document the module and the `court.json` format in the module docstring and verify `python -c "import vball.court_registration"` and the tests pass

## 3. Evaluation in metres

- [x] 3.1 Write `scripts/eval_court_keypoints.py` reporting median and p90 keypoint error in metres plus no-mapping count for the k6y7r test and VNL splits, and verify it runs on the smoke-run weights
- [ ] 3.2 Measure inference time per image on the M1 Pro CPU in the same script and verify it is printed
- [ ] 3.3 After Colab training, run the evaluation on the real weights, record the numbers in README "Status" and CLAUDE.md, and verify they match the script output (no proxy numbers presented as accuracy)
- [ ] 3.4 Tune the status thresholds from the evaluation's error distribution and verify the threshold values are the only edit in `vball.court_registration`

## 4. Pipeline court stage (web app)

- [x] 4.1 Implement `pipeline.court` with `vball.court_registration`, bump the court stage version to 1, and verify backend tests with a fake detector cover ok, failed and unavailable shots
- [x] 4.2 Verify on the 5 evaluation clips that the court stage time is ≤ 0.5 × clip duration and record the timing

## 5. Court API and corrections (web app)

- [ ] 5.1 Add the `court_corrections` table and a single read function that overlays corrections on `court.json`, and verify tests that a correction wins and that clearing restores the model result
- [ ] 5.2 Add `GET /videos/{id}/court` and `PUT` / `DELETE /videos/{id}/court/{shot}` and verify API tests for both, including 404s
- [ ] 5.3 Queue a job from `events` on correction (or rely on the active job) and verify tests that ball results are reused and that no second job is created while one is active
- [ ] 5.4 Verify a rerun from `decode` keeps the correction (test)
- [ ] 5.5 Update the web app `docs/architecture/ARCHITECTURE.md` API table and verify the endpoints listed match `/openapi.json`

## 6. Integration

- [ ] 6.1 Switch `scripts/detect_court.py` to the learned model, render overlays for the 5 clips, and verify by eye that at least 4 of 5 are correct (currently 1 of 5); record the result in README

## Workflow follow-up

- Run `openspec validate add-court-registration --strict` and the verify step before archiving.
- Archive the change so `openspec/specs/court-registration` and `analysis-jobs` reflect the new behaviour.
