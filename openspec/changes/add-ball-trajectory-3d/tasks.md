# Tasks

## 1. Camera calibration (`vball.calibration`)

- [x] 1.1 Implement homography-initialised calibration refined on all keypoints (both net heights, lower error kept) and verify synthetic tests recover a known camera's focal length within 2% and position within 0.2 m from noisy keypoints
- [x] 1.2 Implement the floor-only fallback and the quality gate and verify tests for each status
- [x] 1.3 Measure median reprojection error on the k6y7r test labels and with court model v2 predictions; record both in `docs/results/trajectory.md` and verify against the script output

## 2. Flights (`vball.trajectory`)

- [x] 2.1 Implement flight segmentation (direction change, speed jump, gaps, minimum length) and verify tests on synthetic tracks with known touch frames (cuts within 2 frames)
- [x] 2.2 Implement the synthetic generator (arcs through a known camera, detection noise, occlusions) and verify it reproduces exact projections with zero noise

## 3. Ballistic fit

- [x] 3.1 Implement the fit with robust loss and multiple initialisations and verify on synthetic arcs with 2 px noise: median 3D error ≤ 0.10 m
- [x] 3.2 Fill unobserved frames from the fitted path and verify the 5-frame occlusion scenario
- [x] 3.3 Implement fit error and depth conditioning with low-quality reasons and verify a flight along the line of sight is flagged
- [ ] 3.4 Compare optional drag on real flights from the evaluation clips; record fit errors with and without and the decision

## 4. Derived values

- [x] 4.1 Implement landing point, net-crossing height and position, start speed and apex, and verify on synthetic arcs against analytic values

## 5. Pipeline and API (web app)

- [x] 5.1 Add the `trajectory` stage after `players`, bump the events version, and verify backend tests for order, reuse and the unusable-calibration path
- [x] 5.2 Add `GET /videos/{id}/flights?start=&end=` and verify API tests; regenerate frontend types

## 6. 2D tactics board

- [ ] 6.1 Build the top-down board (ground tracks from 3D, height colour with labels, landing marks, players when present, dashed low-quality flights) as a tab on the match page and verify component tests
- [ ] 6.2 Place the ball marker from the playback clock in an animation frame and verify it follows the playhead without React commits (profiler test)

## 7. 3D tactics board

- [ ] 7.1 Add three.js as a lazy-loaded tab with orbit controls, court, net and flights; verify the main bundle size is unchanged and the tab loads on demand
- [ ] 7.2 Verify by screenshot in both themes that flights and the ball marker match the video at three playback times

## 8. Real-footage checks

- [ ] 8.1 On the evaluation clips, check net-crossing heights are above the net top for balls that crossed and report the share of low-quality flights; record in `docs/results/trajectory.md`
- [ ] 8.2 When labelled landings exist (M5), report landing error against them

## 9. Docs

- [ ] 9.1 Update README status, CLAUDE.md and the PRD acceptance section with measured numbers and verify they cite `docs/results/trajectory.md`

## Workflow follow-up

- Archive after `add-player-tracking`; validate with `openspec validate add-ball-trajectory-3d --strict` and verify first.
