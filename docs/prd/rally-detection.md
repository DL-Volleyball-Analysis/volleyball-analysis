# Rally detection (play / no play), measured

Version 1.0 · 2026-10-11 · Owner: YuJia Liang · Parent: [rally-scoring.md](rally-scoring.md)

## Why
The match page shows demo rallies: the events and rallies stages are still "todo". Scoring, the rally list, the
timeline and every per-rally statistic depend on knowing when a rally is played. A rally detector is the first
part of milestone M3 that can be built and measured with public data.

## What
- **Data:** the game-state dataset of masouduut94/volleyball_analytics (GPL-2.0 code; clips labelled service,
  play, no-play from broadcast matches). If it has no held-out split, one is made by match.
- **Methods compared (an ablation):**
  1. A rule on the ball track (no training): a rally is a stretch where the ball is detected and moving, with
     the upstream's track features (duration, path length, direction changes).
  2. The published VideoMAE game-state checkpoint (Kinetics VideoMAE fine-tuned on that dataset;
     CC BY-NC through its base model, research use).
  3. A small classifier on our own signals (ball track features, players' movement), trained on the dataset's
     training part.
- **Pipeline:** the rallies stage segments the video into rallies with start, end and a confidence, replacing
  the demo rallies; winners stay a user decision until landing calls exist (rally-scoring.md).

## Success
- Window accuracy and per-class F1 on held-out matches, and rally boundary error (start / end within 1 s) where
  rally boundaries are labelled. No number from the dataset's own training clips.
- The rallies stage switches from demo data to detected rallies only with these numbers recorded; demo data
  stays labelled as such until then.

## Out of scope
Point winners, landing calls and serve order (rally-scoring.md); audio.
