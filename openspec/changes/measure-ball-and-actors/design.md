# Design

## Data
Volleyball dataset (Ibrahim et al., CVPR 2016): 4,830 clips of 41 frames (1280 x 720, 8 matches at 1920 x 1080),
official split by match (train 24, validation 15, test 16 matches; test 1,337 clips). Ball position in all 41
frames (Perez et al., Pattern Recognition 2022; (0, 0) = not visible). Player boxes with track ids and action
labels on 9 frames around each key frame (`annot_all.pkl` in the Kaggle copy, CC0). The 62 GB of frames are read in
place on Kaggle; only the 1.6 MB ball annotations and 32 MB box annotations are needed locally.

## Ball: candidates, then a tracker
Detectors only propose candidates (`ball_detect`), so every detector shares the tracker and the ablation is a
grid: detector x {most confident candidate, tracker}. Fixed objects are found by motion, not position, because the
broadcast camera pans: global shift by phase correlation, then the mean absolute grey change of a 17 px patch
against the aligned patches 3 frames before and after (on broadcast clips fixed objects 9-24, the ball 40-85;
threshold 30). Linking is a Viterbi over candidates plus "no ball" with a quadratic step cost and a hard step limit
growing with the gap; gaps up to 5 frames are filled with a quadratic fitted to 4 detections on each side.
Thresholds were set on our own clips, never on the test split.

## Actors: a ball prior
prior = floor + (1 - floor) exp(-(d / (k h))^2), d the distance from the ball to the player's box, h the box height;
applied per frame, then each player's frames are combined by the mean of the top n. Grid over n, k, floor and the
decision threshold on the validation matches by macro F1 of block / receive / set / spike; the chosen setting is
reported once on the test matches. Label mapping: setting -> set, digging -> receive, spiking -> spike, blocking ->
block; serves are not labelled in this dataset, so serve predictions count as wrong.

## Risks
- The Volleyball dataset is from older broadcasts at 720p; numbers may differ on our clips. Reported as such.
- VballNet and RAVEL were not trained on it (cross-dataset), unlike WASB's published volleyball model; the WASB
  reference run is labelled as in-domain.

## Per-player classifier (added 2026-10-11)
The detector measured on this dataset almost never predicts set or receive (macro F1 0.303), and a ball prior cannot
change a wrong class. A YOLO26s-cls classifier on square player crops (box + 15%, `vball.actors.person_crop`, the same
crop in training and in the pipeline) is trained on the 9 person actions of the training matches and selected on
validation. In the actions stage it classifies every player track at the action sampling rate;
`vball.actors.classifier_rows` turns its output, times the ball prior, into the detection rows `vball.actions` already
merges into events, so event merging, suggestions and the API are unchanged. Serves stay with the detector.
