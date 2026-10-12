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
import random
from pathlib import Path

import cv2

from vball.actors import person_crop
from vball.evaluation.actions_volleyball import TEST_MATCHES, VAL_MATCHES, load_annotations

CLASSES = ["blocking", "digging", "falling", "jumping", "moving", "setting", "spiking", "standing", "waiting"]
OFFSETS = (-4, -2, 0, 2, 4)


def split_of(match: int) -> str:
    return "test" if match in TEST_MATCHES else "val" if match in VAL_MATCHES else "train"


def build(videos: Path, pkl: Path, out: Path, margin: float = 0.15, standing_share: float = 0.2, seed: int = 0) -> dict:
    ann = load_annotations(pkl)
    rng = random.Random(seed)
    jobs = []  # (split, class, match, clip, frame, player, box)
    for m, clips in ann.items():
        split = split_of(m)
        offsets = (0,) if split == "test" else OFFSETS
        for c, d in clips.items():
            key = d["frames"].get(c, {})
            for player, (_, label) in key.items():
                for o in offsets:
                    fb = d["frames"].get(c + o, {}).get(player)
                    if fb is not None:
                        jobs.append((split, label, m, c, c + o, player, fb[0]))
    # thin 'standing' in train / val so it is at most standing_share of the split
    kept = []
    for split in ("train", "val", "test"):
        js = [j for j in jobs if j[0] == split]
        if split != "test":
            stand = [j for j in js if j[1] == "standing"]
            other = [j for j in js if j[1] != "standing"]
            n = int(standing_share / (1 - standing_share) * len(other))
            js = other + rng.sample(stand, min(n, len(stand)))
        kept += js
    counts: dict = {}
    for split, label, m, c, f, player, box in kept:
        img = cv2.imread(str(videos / str(m) / str(c) / f"{f}.jpg"))
        if img is None:
            continue
        x = person_crop(img, box, margin)  # the same crop the pipeline classifies
        if x is None or x.size == 0:
            continue
        d = out / split / label
        d.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d / f"{m}_{c}_{f}_{player}.jpg"), x, [cv2.IMWRITE_JPEG_QUALITY, 92])
        counts[(split, label)] = counts.get((split, label), 0) + 1
    return counts
