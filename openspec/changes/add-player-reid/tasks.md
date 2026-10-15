# Tasks

## 1. Measure
- [x] 1.1 Tracking evaluation: switches for appearance matching and track joining; time per frame in the report
- [x] 1.2 BoT-SORT with `with_reid` (detector features) on SportsMOT volleyball validation; record in docs/results/player-tracking.md

## 2. Trained embedding (only if 1.2 misses IDF1 0.75)
- [ ] 2.1 Crop dataset from SportsMOT volleyball training sequences (identities per sequence), notebook for Kaggle/Colab
- [ ] 2.2 Train, add to models/manifest.json, evaluate in the tracker

## 3. Join broken tracks
- [ ] 3.1 `vball.reid.join_tracks` with appearance, court speed, side, team and shirt-number checks; tests
- [ ] 3.2 Evaluate on validation; thresholds from training sequences

## 4. Adopt
- [ ] 4.1 Players stage uses the adopted steps; stage version bump; golden check on the other stages
- [ ] 4.2 Results, README and papers updated with the measured change (also if nothing is adopted)
