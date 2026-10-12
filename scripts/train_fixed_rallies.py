"""Fixed-camera rally model: trained on score-bug labels of full matches, tested on other matches (change
label-rallies-from-score, task 2.2).

Labels (scripts/label_rallies.py) give the time each point appeared on the score bug, i.e. the end of a rally plus
the bug's delay, but no rally starts. Training samples are therefore labelled weakly: play in the PLAY_S seconds
before each rally end (bug time minus DELAY_S), no play from GAP_S after a rally end until GAP_S before the next
rally's play window; everything else is left out. The evaluation does not rest on those assumptions: a detected rally
counts when its end is followed by a point change on the bug within END_WINDOW_S (one to one, in time order), so
precision and recall are over points, and the delay from detected end to bug update is reported.

Cues: `vball.rally_cues.stage_cues` (scripts/extract_stage_cues.py). Classifier and segmentation as for broadcasts
(vball.rallies), segmentation thresholds chosen by leave-one-match-out on the training matches.

  .venv/bin/python scripts/train_fixed_rallies.py --test-cues outputs/rallies/fixed_cues \\
      --test-labels outputs/rallies/score_labels [--save models/rally_fixed_hgb.joblib]
"""
import argparse
import json
from pathlib import Path

from vball.evaluation.fixed_rallies import COLUMNS, RATE, choose_config, evaluate, fit, load
from vball.paths import DATASETS
from vball.rallies import save_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-cues", type=Path, default=DATASETS / "watchdog" / "cues")
    ap.add_argument("--train-labels", type=Path, default=DATASETS / "watchdog" / "labels")
    ap.add_argument("--test-cues", type=Path, required=True)
    ap.add_argument("--test-labels", type=Path, required=True)
    ap.add_argument("--save", type=Path, default=None)
    args = ap.parse_args()
    train, test = load(args.train_cues, args.train_labels), load(args.test_cues, args.test_labels)
    print(f"train: {len(train)} matches, {sum(len(c) for c, _ in train.values())} samples, "
          f"{sum(len(ch) for _, ch in train.values())} points; test: {len(test)} clips, {sum(len(ch) for _, ch in test.values())} points")
    cfg = choose_config(train)
    model = fit(train)
    res = evaluate(model, test, cfg)
    print("segmentation:", cfg)
    print(json.dumps({k: v for k, v in res.items() if k != "per_match"}))
    for name, v in res["per_match"].items():
        print(f"  {name}: {v}")
    if args.save:
        save_model(args.save, model, cfg, RATE, {"train": sorted(train), "test": res}, COLUMNS)


if __name__ == "__main__":
    main()
