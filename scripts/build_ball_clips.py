"""Ball training clips in one format from the public labelled sources (change train-ball-detector).

Every clip becomes a folder of consecutive frames letterboxed to the detector's input (512 x 288, the transform of
vball.ball_detect.Wasb) and `labels.csv` (frame, visible, x, y in input pixels; x = y = -1 when no ball). A manifest
lists source, match, clip, split, frames and visible frames.

Sources and splits (by match, so no match is in two splits):
  volleyball  the Volleyball dataset (Ibrahim et al., CVPR 2016) with Perez et al.'s ball positions: 41-frame clips;
              test = the official 16 test matches, train = all others (as WASB trains).
  orel        volleyball-orel.ru `data_20250711_2330` (indoor gyms, VballNet's author): videos with per-frame
              Frame,Visibility,X,Y CSVs; test = the matches in OREL_TEST (a backline and a side view), the beach match
              is left out, train = the rest. The author's own train/test folders split videos of the same
              matches, so they are merged and re-split here.

  python scripts/build_ball_clips.py --out <dir> [--volleyball-videos <dir> --volleyball-ann <dir>] [--orel <dir>]
"""

import argparse
from pathlib import Path

from vball.datasets.ball_clips import build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--volleyball-videos")
    ap.add_argument("--volleyball-ann")
    ap.add_argument("--orel")
    args = ap.parse_args()
    vb = (Path(args.volleyball_videos), Path(args.volleyball_ann)) if args.volleyball_videos else None
    m = build(Path(args.out), vb, Path(args.orel) if args.orel else None)
    print(
        m.groupby(["source", "split"])[["frames", "visible"]].sum().assign(clips=m.groupby(["source", "split"]).size())
    )


if __name__ == "__main__":
    main()
