# Tasks

## 1. Labels
- [ ] 1.1 Download eight full matches (720p, local only) — 6 of 8; two blocked by YouTube 403
- [x] 1.2 `vball.scorebug`: read, clean, point changes; tests on cropped score images and synthetic sequences
- [ ] 1.3 `scripts/label_rallies.py`; check two matches by hand (every change found, no false ones); measure the update delay

## 2. Fixed-camera rallies
- [x] 2.1 Rally cues from pipeline results (court status, placed players and their motion, ball)
- [ ] 2.2 Train and evaluate by match; rallies stage uses it for still cameras; docs/results/rallies.md — trained and evaluated (F1 0.76 on the six fixed clips, docs/results/rallies.md 2026-10-13); stage integration pending
