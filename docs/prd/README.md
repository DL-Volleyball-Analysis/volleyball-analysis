# Volleyball Analysis — Product Requirements

Version 1.0 · 2026-10-08 · Owner: YuJia Liang

This PRD answers *why, for whom, and what counts as success*. How the system must behave is in `openspec/specs/`; each change's design and task breakdown is in `openspec/changes/<change>/`.

| Document | Covers |
|---|---|
| this file | vision, users, goals, scope, milestones |
| [court-registration.md](court-registration.md) | automatic court detection from any camera angle |
| [ball-tracking.md](ball-tracking.md) | more accurate ball tracking |
| [rally-scoring.md](rally-scoring.md) | landing, rally segmentation, automatic scoring |
| [match-review.md](match-review.md) | match review interface (web app) |
| [landing-page.md](landing-page.md) | public landing page (volleyvision-website) |
| [player-tracking.md](player-tracking.md) | player detection, tracking, court positions |
| [tactics-board.md](tactics-board.md) | 3D ball trajectory, 2D / 3D tactics board |
| [player-stats.md](player-stats.md) | attack efficiency and serve statistics from coach tags |
| [player-actions.md](player-actions.md) | action events and shirt numbers per player, suggested tags |

Background: analysis of the capstone web app in [`docs/webapp_redesign.md`](../webapp_redesign.md); organisation-wide repo plan in [`docs/repo-organization.md`](../repo-organization.md).

## 1. Vision
Turn a single-camera volleyball recording into a point-by-point match record — how each point started, where the ball landed, who won it — without marking the court or keeping score by hand.

## 2. Users and situations
| User | Situation | Cares most about |
|---|---|---|
| Coach (primary) | After a match, reviews a phone/laptop recording to find patterns in lost points | correct score, jumping to any point, landing distribution |
| Player | Rewatches the rallies they played in | finding their moments |
| Researcher (owner) | Research demonstrations; base for 3D trajectory research | trustworthy accuracy, reproducibility, clean architecture |

**Deployment assumption:** single-user, runs on the user's own computer, no accounts (see §7 Q1).

## 3. Problems
1. **Manual court marking.** The capstone needed four clicks per video and judged landings with hard-coded pixel thresholds (`y_abs_min=640`), which break at any other angle.
2. **No scoring.** The capstone's score field is always empty; rallies are "any detection in this frame".
3. **Weak ball tracking on wide shots.** Only 28% of frames detected on the high-angle men's broadcast clip.
4. **The interface hides what matters.** Only an overlay video; no score, rally list or landing map.

## 4. Goals and non-goals
**Goals**
- G1: Find the court automatically for common camera positions (behind the end line, high on the side, broadcast) with no clicks.
- G2: Segment rallies and decide the point winner automatically; corrections take one key press.
- G3: An interface centred on score and rallies; any point reachable in two clicks.
- G4: Every accuracy number backed by labelled data; proxies and labelled accuracy are reported separately.

**Non-goals (this version)**
- Live analysis during a match.
- Multi-camera fusion. (Single-camera 3D trajectory reconstruction is in scope: tactics-board.md.)
- Accounts, cloud deployment, collaboration.
- Player action recognition and jersey numbers (no accuracy data for the capstone models; optional and off by default, see §7 Q2). Player detection and tracking themselves are in scope (player-tracking.md).

## 5. Success metrics
| Metric | Target | Measured by |
|---|---|---|
| Court corner error | median < 0.3 m in court coordinates | k6y7r test + VNL external split, evaluation script |
| Ball detection F1 | ≥ 0.85 on own gym footage | labelled frames, `metrics.accuracy` |
| Rally segmentation | ≥ 90% of rally starts/ends within ±1 s | labelled full set |
| Point winner accuracy | ≥ 90%, low-confidence rallies flagged | labelled full set; VNL-STES score events |
| Correction effort | ≤ 2 minutes per set | timed |

A metric without labelled data is reported as "not measured", never replaced by a proxy.

## 6. Scope and milestones
| Milestone | Content | Tracked in |
|---|---|---|
| M1 Court | keypoint model, homography, court corrections | court-registration · OpenSpec `add-court-registration` |
| M2 Interface | new frontend: library, match page, scoreboard, rally list (demo data first) | match-review · OpenSpec `rebuild-match-review-ui` |
| M3 Landing & scoring | landing detection, in/out, rally segmentation, point winner | rally-scoring (change to be opened) |
| M4 Ball tracking | small/wide ball: higher input resolution, tiling, TrackNetV5 comparison | ball-tracking (change to be opened) |
| M5 Evaluation | label own full-set footage, measure every metric | each PRD's success metrics |
| Site | landing page with honest claims and the new UI | landing-page · OpenSpec `refresh-landing-page` |
| Players | detect and track on-court players, positions in metres (baseline first, train only if needed) | player-tracking · OpenSpec `add-player-tracking` |
| Trajectory | camera calibration, 3D ball flights, 2D / 3D tactics board | tactics-board · OpenSpec `add-ball-trajectory-3d` |
| Stats | rosters, attack / serve tags, attack efficiency (phase 1: coach tags) | player-stats · OpenSpec `add-player-stats` |

M1 and M2 run in parallel; M3 needs M1's court coordinates. The site refresh removes false claims now and adds screenshots after M2.

## 7. Open questions
| # | Question | Current assumption |
|---|---|---|
| Q1 | Only on the owner's computer, or shared with the team? | single-user local |
| Q2 | Keep player / action / jersey features? | optional, off by default; revisit after M5 |
| Q3 | When will own full-set match videos be available? (needed for M3, M5) | waiting on the owner |
