# Player actions and shirt numbers

Change: `openspec/changes/add-player-actions`.

## Models (2026-10-10)
| Model | File (`models/`, not in git) | Source run |
|---|---|---|
| Actions, YOLOv11m, 5 classes (block, receive, serve, set, spike), 640 px | `action_yolo11m.pt` | team Drive `專題/vb_action_yolov11/runs/volleyball_200epoch/weights/best.pt` (epoch 190 of 200) |
| Jersey digits, YOLOv8m, 10 classes (0-9), 640 px | `jersey_digits_yolov8m.pt` | team Drive `專題/jersey-number-detection-main/runs/jersey_detection/weights/best.pt` |

## Action recogniser on its test split
`scripts/eval_actions.py --train-zip <capstone zip>` (output kept in `outputs/actions_eval.txt`). The capstone's
dataset (the same 18,616 / 3,636 / 2,554 split as the report) was taken from the capstone zip on the team Drive;
the test split was never used for training or model selection.

| | AP@0.5 | AP@0.5:0.95 |
|---|---|---|
| all (precision 0.952, recall 0.937) | **0.957** | **0.790** |
| block | 0.987 | 0.797 |
| receive | 0.863 | 0.679 |
| serve | 0.967 | 0.751 |
| set | 0.976 | 0.845 |
| spike | 0.991 | 0.879 |

**Not an unseen-match score.** The 1,222 test images that carry a source video name all come from videos that
are also in the training split (100%); the training split has 10 named sources, and 53% of its images are
unnamed screenshots whose source cannot be told. Frames from one video are near duplicates, so 0.957 says how
well the model knows these matches, not how it does on a new one. An independent test needs our own labelled
footage (PRD M5).

## Class distribution and gaps
| Split | Images | Boxes | Images without a box | block | receive | serve | set | spike |
|---|---|---|---|---|---|---|---|---|
| train | 18,616 | 16,878 | 4,219 (22.7%) | 4,608 (27.3%) | 984 (5.8%) | 2,348 (13.9%) | 4,147 (24.6%) | 4,791 (28.4%) |
| valid | 3,636 | 3,129 | 1,207 (33.2%) | 1,072 (34.3%) | 277 (8.9%) | 340 (10.9%) | 495 (15.8%) | 945 (30.2%) |
| test | 2,554 | 2,269 | 593 (23.2%) | 574 (25.3%) | 157 (6.9%) | 275 (12.1%) | 550 (24.2%) | 713 (31.4%) |

- **Receive is scarce**: 984 training boxes against 4,791 for spike (about 1 to 5), and it is the weakest class
  (AP 0.863). Reception quality is one of the things coaches review most, so this gap matters.
- **No dig or free-ball class**: defensive touches after the first contact have no label of their own, so they are
  either unlabelled or folded into receive.
- **Mostly one box per image**: images label the acting player (block allows up to 5 boxes); other players in
  the frame are not "no action" examples, so the model's behaviour on them is untested.
- **Few matches**: about 6,450 of the named training frames come from three amateur league games (PS vs Blockparty,
  NY Urban, Big City Co-Ed 6s), plus a club tour clip and an U20 world championship final. Amateur footage is the
  product's target, but a handful of courts and teams is narrow.
- **Background share differs by split** (22.7% / 33.2% / 23.2%).

Consequences for the plan: report receive separately and treat receive events as less reliable; collect and label
receive and dig frames from our own matches before relying on reception statistics.
