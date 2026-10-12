"""Player tracking accuracy on labelled volleyball sequences (SportsMOT volleyball, MOT format).

Runs `vball.players.track_frames` on each sequence and scores it with TrackEval (the reference
HOTA implementation, unmodified in external/TrackEval): HOTA, IDF1, MOTA, detection recall and
precision, plus CPU time per detected frame. Results are labelled data, never proxies.

Usage:
  .venv/bin/python scripts/eval_player_tracking.py --model yolo26n.pt --imgsz 960 --tracker botsort.yaml --det-fps 10
  .venv/bin/python scripts/eval_player_tracking.py --gt-as-tracker      # sanity check: must score 1.0
  options: --seqs N (first N volleyball sequences), --max-frames N (per sequence, for quick runs)
"""

import argparse

import numpy as np
import pandas as pd

from vball.evaluation.player_tracking import evaluate, gt_as_tracker, run_tracker, volleyball_val_seqs
from vball.players import TrackerConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolo26n.pt")
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--tracker", default="botsort.yaml")
    ap.add_argument("--det-fps", type=float, default=10.0)
    ap.add_argument("--seqs", type=int, default=None, help="only the first N volleyball sequences")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--gt-as-tracker", action="store_true")
    args = ap.parse_args()

    seqs = volleyball_val_seqs()[: args.seqs]
    if args.gt_as_tracker:
        label, ms = "ground_truth", {}
        gt_as_tracker(seqs, label, args.max_frames)
    else:
        cfg = TrackerConfig(args.model, args.imgsz, args.tracker, args.det_fps)
        label = cfg.label() + (f"_first{args.max_frames}" if args.max_frames else "")
        print(f"{label} on {len(seqs)} volleyball validation sequences")
        ms = run_tracker(seqs, cfg, label, args.max_frames)
    table = evaluate(seqs, label, args.max_frames)
    if ms:
        table["ms_per_detected_frame"] = pd.Series(ms)
        table.loc["COMBINED_SEQ", "ms_per_detected_frame"] = float(np.median(list(ms.values())))
    # COMBINED_SEQ is TrackEval's own combination over all sequences (metrics recomputed from the
    # pooled matches); averaging per-sequence HOTA or IDF1 would be wrong.
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()
