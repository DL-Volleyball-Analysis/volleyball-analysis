"""Build a player-only detection set (YOLO format, one class) from SportsMOT volleyball training sequences.

SportsMOT labels only the players on court; referees, coaches, the bench and spectators are distractors by design,
so a detector fine-tuned on these labels learns to leave them out (change filter-on-court-players). Every
`--every`-th frame is kept (consecutive frames are near duplicates). The 15 training sequences come from 5 match
videos; the validation split holds out whole videos. SportsMOT's own volleyball validation sequences are never
used here: they stay for the tracking evaluation (scripts/eval_player_tracking.py).

Licence: SportsMOT is CC BY-NC 4.0 (research use, not redistributed). Runs where the data is, e.g. on Kaggle:

  python scripts/build_sportsmot_detection.py --src <dir with train/<seq>/...> --out <dir> [--every 3]
"""

import argparse
from pathlib import Path

from vball.datasets.sportsmot_detection import VOLLEYBALL_TRAIN, build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder holding the sequences (SportsMOT train/)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=3)
    ap.add_argument("--seqs", nargs="*", default=VOLLEYBALL_TRAIN)
    args = ap.parse_args()
    print("images:", build(Path(args.src), Path(args.out), args.seqs, args.every))


if __name__ == "__main__":
    main()
