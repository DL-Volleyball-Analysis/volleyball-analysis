# PRD: Player actions and shirt numbers

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-player-actions/`

## Problem
The rebuilt system tracks players but does not know what they do or who they are: boxes carry tracking ids,
not shirt numbers, and the capstone's action recogniser (YOLOv11m, five actions, validation mAP@0.5 0.945) and
jersey-number detector (YOLOv8m, digits 0-9, validation mAP@0.5 0.966) are not used. Coaches read players by
shirt number, and attack statistics need to know who attacked; today every attack is tagged by hand.

## User stories
- As a coach, I see each player's shirt number on the video and the court map, not an internal id.
- As a coach, I see when a player served, received, set, spiked or blocked, on the timeline and the video.
- As a coach, the system suggests attack and serve tags (who, when) and I accept or fix them, instead of
  typing every tag.
- As a researcher, I know how accurate the action and number models are on held-out data before trusting
  any statistic built on them.

## Requirements
1. Measure both capstone models on their datasets' test splits (never used for training or model selection):
   action mAP@0.5 per class; jersey digit mAP and whole-number accuracy on player crops.
2. An actions stage after player tracking: action detections at a configurable rate, each assigned to the
   overlapping player track, merged into action events (player, action, start, end, confidence).
3. Shirt numbers per track: digits detected inside player boxes on sampled frames, composed left to right
   into a number per frame, and a per-track vote with its share of agreeing frames; a number is shown only
   when the vote is clear, otherwise the tracking id.
4. Display: numbers on video boxes, the court map and the rendered video; action events as a timeline lane
   and in the rendered video.
5. Suggested tags: spike and serve events become suggested attack / serve tags (team from the side of the net,
   number from the vote); suggestions are marked, never counted until the coach accepts them.
6. Everything without enough evidence (no number vote, low-confidence action) is shown as unknown, not guessed.

## Acceptance criteria
- Test-split numbers recorded in `docs/results/actions.md` before the stage is enabled by default.
- A rendered evaluation clip shows numbers matching the shirts on players with a clear vote (checked by eye).
- Accepting a suggestion produces exactly the tag a coach would have typed (tests).

## Out of scope
- Training new action or number models (only if the measurements demand it, as a separate change).
- Re-identification across shots and matches.

## Dependencies
- Player tracking (add-player-tracking); side of the net needs a usable court (add-court-registration).
- Player statistics (archived add-player-stats) for the tags the suggestions become.
