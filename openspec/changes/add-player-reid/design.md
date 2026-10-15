# Design

## Context
Detector: YOLO26s fine-tuned on SportsMOT volleyball players, 960 px, detection at 10 Hz, BoT-SORT (ultralytics
defaults, `with_reid: False`). Shirt numbers are already voted per track (actions stage).

## Decisions

**Measure the free option first.** Ultralytics BoT-SORT can use the detector's own feature maps as appearance
(`model: auto`). It costs no training and little time; it sets the bar the trained embedding must beat.

**Trained embedding, if needed.** SportsMOT gives identities within each sequence, enough to train a metric embedding
(an OSNet-size or YOLO26-cls backbone, triplet or ID loss) where negatives come from the same match: teammates in the
same shirt are exactly the hard cases. Crops: the player box widened as in the action classifier. Training on Kaggle
or Colab, inference on CPU at 10 Hz on at most ~14 boxes per frame.

**Join tracks offline.** Most breaks are long gaps (exits, pauses), which online association cannot bridge with a
30-frame buffer. After tracking, tracks that never coexist are candidates; a merge needs: appearance distance below a
threshold chosen on training sequences, court speed between the end of one and the start of the other below 8 m/s
(when a court exists), same side and team, no conflicting shirt number. Greedy merging by distance, never more than
twelve concurrent on-court ids.

**Adoption rule.** Each step is a switch in the evaluation; a step goes into the pipeline only if IDF1 rises and HOTA
does not fall on the validation sequences. Parameters are chosen on training sequences, never on validation.

## Risks
- Appearance of teammates is nearly identical: the trained embedding may add little; the shirt number and court
  movement then carry the joins.
- Wrong merges are worse than splits for statistics: thresholds favour precision.
