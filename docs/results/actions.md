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

## Jersey digit model: the training labels are wrong (2026-10-10)
The capstone merge script (`training/jersey-numbers/organize_datasets.py`) maps class *indices* across datasets
and ignores class *names*. Index order of the four merged Roboflow sets (Roboflow sorts names):

| Dataset | Classes by index | Became |
|---|---|---|
| volleyai-actions/jersey-number-detection-s01j4 | 0-9 | digits 0-9 (correct) |
| workspace67/jersey-fxmll | 0-9 | digits 0-9 (correct) |
| teste-5efoz/player-number-detect (565 train images) | Ball, Player, number | "0" = ball, "1" = whole player, "2" = whole number |
| hgjhj/jersey-number-detection-br3ld (612 / 175 / 87) | number | "0" = whole number |

Checked against the model: on the 87 hgjhj test crops (one whole-number box each) it predicts class "0" 93
times, 86 of them on the whole-number box (IoU > 0.5) - it learned "0" as "a number is here". The validation
mAP@0.5 of 0.966 includes these wrong labels, so it does not measure digit reading. On full broadcast frames
it detects nothing (trained on crops), so it would need player crops anyway.

Consequence: the model cannot be used to read shirt numbers. A correct merge (map by class name, drop Ball and
Player, keep whole-number boxes only as a separate class or not at all) and a retrain on Colab are needed before
task 1.3 can measure anything meaningful. None of the three datasets with digit labels has a test split; one
has to be held out by source video.

A second problem: the capstone trained with Ultralytics' default `fliplr: 0.5`
(`training/jersey-numbers/results/args.yaml`), so half the training crops were mirrored; a mirrored digit is a
different digit and a mirrored two-digit number reads backwards.

## Jersey digit retraining set (2026-10-11)
`scripts/build_jersey_dataset.py` -> `data/datasets/jersey_digits.zip` (on Drive for
`notebooks/train_jersey_digits.ipynb`, YOLO26s, 320 px, `fliplr=0`).

- Classes mapped by name ('0'-'9', 'cero'); only sets with digit boxes. Both volleyball sets (v1 exports) have
  exactly the classes 0-9; the two capstone sets with ball / player / whole-number boxes are left out.
- Split by match, not frame. The Roboflow splits put frames of all 10 matches in both train and valid, which is
  why the capstone's validation score could not show generalisation.
- A baseball and football set with digit boxes (practice-qj7kd/jersey-number-cogss, 1,004 crops, CC BY 4.0)
  is added to train only, for more fonts, colours and poses; valid and test stay volleyball.

| Split | Crops | Matches | Fewest boxes |
|---|---|---|---|
| train | 5,720 | usm_ft_1, graz_1 (+ part 2), chile_usa, usm_ucen_2_full + cogss | digit 8: 293 |
| valid | 1,170 | usa_brazil_fem_brazilside, usm_usach_1 (one match alone lacks digits 3 and 4) | digit 7: 74 |
| test | 1,048 | japan_poland, thailand_warmup, poland_italy (teams in no training match) | digit 6: 40 |

Other public data checked: projectexperiments/jersey-detection-v3 (8,617 images) labels whole numbers as 103
classes, usable later to test whole-number reading but not to train digit boxes; SoccerNet and the hockey set of
Koshkina and Elder label whole numbers per crop or tracklet, which suits a text-recognition reader (PARSeq)
rather than a digit detector.

## Retrained digit model (2026-10-11)
`notebooks/train_jersey_digits.ipynb` on Kaggle (T4): YOLO26s, 320 px, no flips; early stop at epoch 69 (patience
40), best validation mAP@0.5:0.95 0.521 at epoch 29; 36 min. Installed as `models/jersey_digits_yolo26s.pt`.

**Digits, test split** (1,048 crops; Japan, Thailand and Poland, teams in no training match):
mAP@0.5 **0.824**, mAP@0.5:0.95 0.519, precision 0.809, recall 0.740.

| digit | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| AP@0.5 | 0.690 | 0.932 | 0.936 | 0.904 | 0.810 | 0.906 | 0.767 | 0.890 | 0.681 | 0.727 |

**Whole numbers, one crop at a time** (`scripts/eval_jersey.py`, output in `outputs/jersey_eval.txt`): read exactly
**63.2%**, wrong 29.9%, not read 7.0%; one-digit numbers 70.8% / 12.4% / 16.8%, two-digit numbers 60.1% / 36.8% /
3.1%. The most common error drops one digit of a two-digit number (19 -> 1, 11 -> 1, 15 -> 1, 17 -> 7), then
look-alike digits (18 -> 16, 5 -> 9). The web app votes over a track's readings (at least 3, 60% agreeing), which
should raise accuracy per player; that is not measured yet (no labelled tracks with numbers).

## On the evaluation clips (2026-10-11)
The actions stage now runs with both models installed. Per clip: 8-21 action events, 1-8 tracks with a shirt
number. Checked by eye on the rendered back view (Tokyo 2020, no usable court) at 4.1 s:
- right: the libero labelled #27, a red #24, and "ID 10 spike" on the attacker (action right, number not read, so
  no guess);
- wrong: "#27 block" on the blue #14 at the net. Track 6 voted #27 from earlier frames: the tracker swapped
  identities between players, and the vote keeps the old number. Two tracks were also both voted #7 and two #27.
Next: split a track where its readings change consistently (an identity switch) before voting, and measure
number accuracy per player once a clip has labelled numbers.
