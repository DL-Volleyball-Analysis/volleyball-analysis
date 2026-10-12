"""Person action crops from the Volleyball dataset, for a per-player action classifier.

The Volleyball dataset (Ibrahim et al., CVPR 2016) labels every player at each clip's key frame with one of 9
actions (blocking, digging, falling, jumping, moving, setting, spiking, standing, waiting); `annot_all.pkl` holds
the boxes, tracked over 9 frames around the key frame. Crops are written as an image-classification folder
(<split>/<class>/<name>.jpg) with the official split by match.

  train / val: the key frame and frames key +-2 and +-4 of every player (5 views of each action); 'standing'
               is thinned to `--standing-share` of a split's crops, since it is 70% of all players.
  test:        the key frame only, every player (the usual protocol for person action accuracy).
Each crop is the box widened by `--margin` on every side (arms and the ball near the hands stay in view), then
padded to a square with grey (classifiers resize or centre-crop to a square; a tall player would lose head or feet).

  python scripts/build_volleyball_actions.py --videos <dir with <match>/<clip>/<frame>.jpg> \
      --pkl annot_all.pkl --out <dir> [--margin 0.15] [--standing-share 0.2]
"""

import argparse
from pathlib import Path

from vball.datasets.volleyball_actions import CLASSES, build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", required=True)
    ap.add_argument("--pkl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--margin", type=float, default=0.15)
    ap.add_argument("--standing-share", type=float, default=0.2)
    args = ap.parse_args()
    counts = build(Path(args.videos), Path(args.pkl), Path(args.out), args.margin, args.standing_share)
    for split in ("train", "val", "test"):
        print(split, {c: counts.get((split, c), 0) for c in CLASSES})


if __name__ == "__main__":
    main()
