# Design

## Context

- Player tracks (`players.csv.gz`): boxes per frame with track ids, court position and side when the court is ok.
- Capstone models: action YOLOv11m (block, receive, serve, set, spike; 640 px; trained on merged Roboflow sets,
  validation mAP@0.5 0.945, no test evaluation recorded); jersey YOLOv8m detecting single digits 0-9 (640 px,
  validation mAP@0.5 0.966). Weights on the team Drive.
- Tags and statistics: `vball.stats`, web app tags table (archived change add-player-stats).

## Goals / Non-Goals

**Goals:** measured models; actions and numbers tied to tracks; suggestions that save typing without silently
changing statistics. **Non-Goals:** new training, re-identification.

## Decisions

### Measure first
`scripts/eval_actions.py` and `scripts/eval_jersey.py` download the datasets' test splits (Roboflow, the
`ROBOFLOW_API_KEY` from the environment) and run `model.val(split='test')`; the jersey script also scores whole
numbers on player crops by composing digits. The actions stage stays opt-in until both are recorded.

### Module ownership
| Responsibility | Module |
|---|---|
| Assign action boxes to tracks, merge into events | new `vball.actions` |
| Compose digits into numbers, vote per track | new `vball.jersey` |
| Stage wiring, `actions.json`, API | web app `pipeline.py`, `main.py` |
| Labels, Actions lane, suggestions | web app `src/match`, `src/stats`, `render.py` |

### Rates and crops
Actions at 10 fps on the full frame (the model was trained on full frames). Digits at 2 fps per track on the
upper half of the player box upscaled to 640 px (numbers are on the back and chest; the model saw crops).

### Assignment and merging
An action box goes to the track with the highest IoU above 0.3. Consecutive samples (gap at most 3 samples) of
one action by one track merge into an event; peak confidence kept; events below 0.6 peak are dropped (the
capstone's threshold).

### Composing and voting
Digits with confidence above 0.5 inside a crop, sorted by x; at most two digits; a reading is the digits joined.
Per track: the most frequent reading, its share of readings and the count; a number needs at least 3 readings
and a share of at least 0.6.

### Suggestions
Spike events become attack suggestions, serve events serve suggestions, at the event's start time. They live
in `actions.json`, never in the tags table; accepting posts a normal tag (same endpoint) and records the
suggestion as accepted so it is not offered again.

## Risks / Trade-offs

- [Validation-only numbers may be optimistic (frame-level splits)] → test-split measurement first; the stage
  stays opt-in otherwise.
- [Numbers unreadable at broadcast distance] → vote threshold; tracking id shown instead of a guess.
- [Model licences] → datasets are CC BY 4.0; weights stay out of git.
