# PRD: Landing, rallies and automatic scoring

Parent: [README.md](README.md) · OpenSpec: `openspec/specs/match-scoring/` (scoring rules, implemented); the rally detection change opens at M3

## Problem
The capstone's score field is always empty and a "rally" is any frame with a detection. What coaches want most — the score and how each point ended — does not exist.

## User stories
- As a coach, opening a match shows the score of every set, who won each point and why (landed in, out, net, fault).
- As a coach, rallies the system is unsure about are flagged; pressing `1` / `2` sets the right winner and later scores recompute.
- As a researcher, my corrections double as labels for measuring accuracy.

## Requirements
**Rally segmentation**
1. From the ball trajectory and court coordinates, find each rally's start and end (serve to dead ball).
2. Each rally has: start/end time, winner, end reason, confidence, landing point in court metres (empty if it did not land).

**Point winner**
3. Ball lands in → the team on the other side from the landing wins; ball out → the opponent of the last team to touch it wins (lower confidence when the last touch is unclear).
4. The side is decided in court coordinates (`side_of_net`), never by pixel thresholds; the line counts as in.
5. Teams A/B change ends every set; the user states once which team starts on which side, then ends switch automatically.

**Scoring rules** (implemented in `vball.scoring`)
6. Sets to 25 (15 in the fifth) with a 2-point lead; best of five.
7. User corrections win over the model; all later scores recompute after a correction.

## Landing detection: approach with one camera
Tennis (Hawk-Eye: 10 cameras at 340 fps, within the ITF's 5 mm limit) and professional volleyball (FIVB's challenge system: 16-19 cameras) call bounces by triangulating the ball in 3D from many synchronised cameras. We have one camera, so the method is different and the accuracy will be lower (expected tens of centimetres, to be measured):
1. **Physics in 3D:** the court keypoints include the net band, which calibrates the camera fully. Between touches the ball follows a ballistic arc; fit it to the 2D track and intersect with the floor (z = 0) to get the landing point, even when the landing frame is hidden by a player.
2. **Learned event spotting**, as TTNet does for table tennis (single camera, bounce events): a model trained on volleyball event labels (VNL-STES) marks landings and touches in time.
3. **Sound:** the ball hitting the floor is loud and sharp in gym recordings; an audio onset fixes the time, vision fixes the place.
Calls close to a line are reported with their uncertainty and flagged for review rather than decided silently.

## Acceptance criteria
- ≥ 90% of rally starts/ends within ±1 s (own full-set footage, labelled).
- Point winner accuracy ≥ 90%; recall of low-confidence flags ≥ 80% (most errors get flagged).
- Same metrics reported on VNL-STES clips with score events.

## Out of scope
- Player-level statistics (who attacked, who erred), pending the player feature review.
- Rotation and serving-order checks.

## Dependencies
- Court coordinates (court-registration).
- Own full-set match videos (README §7 Q3).
