# Design

## Model
WASB's HRNet (high-resolution branch kept through the network; 3 RGB frames at 512 x 288, ImageNet-normalised; 3
heatmaps out, 1.5 M parameters), initialised from WASB's published Volleyball-dataset weights. Loss as in WASB: focal
loss on binary Gaussian targets, then quality focal loss on real-valued targets. WASB's code is cloned at run time
(MIT) and imported; our trainer, dataset and evaluation live in the repository.

## Clip format
Every source becomes clips of consecutive frames with one row per frame: visible, x, y in original pixels. Training
samples are 3-frame windows; frames are letterboxed to 512 x 288 with the same transform as inference
(`vball.ball_detect.Wasb.prep`). Augmentation: horizontal flip (labels mirrored), colour jitter, small scale and shift.

## Splits (by match)
- Volleyball dataset: train = WASB's training matches (train + validation lists), test = the official 16.
- orel: held-out = one side-view and one backline match chosen before training, the rest train.
- Volleylitics: only file-name sequences (match / rally / frame) of at least 3 consecutive frames; its own valid/test
  splits are not used for model selection.
Model selection on a validation slice of the training matches (a few clips per match), never on test matches.

## Training mixes (the research question)
1. WASB weights, no training (reference). 2. Fine-tuned on broadcast only. 3. Fine-tuned on broadcast + gym.
Each evaluated on both test sets.

## Risks
- orel licence is not stated: research use, not redistributed; weights trained on it are used for research only.
- Volleylitics frames may not be consecutive; only verified sequences are used.
- Kaggle GPU quota (30 h / week): training budget about 6 h per mix.
