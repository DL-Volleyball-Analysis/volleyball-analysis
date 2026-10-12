"""Rally-end and point-winner labels from the on-screen score (change label-rallies-from-score, vball.scorebug).

Reads the score bug once per second in every video of a folder and writes labels/<video stem>.json:
{"video", "fps", "duration_s", "read_share", "missed_points", "changes": [{"t", "team", "score": [sets_a, points_a, points_b, sets_b],
"new_set"}]}. `t` is when the new score was first read; the rally ended a few seconds earlier (the bug updates after
the referee's call; measured in docs/results/rallies.md).

  .venv/bin/python scripts/label_rallies.py                      # data/datasets/watchdog/videos -> labels
  .venv/bin/python scripts/label_rallies.py --videos data/videos/fixed --out outputs/rallies/score_labels
"""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

import cv2

from vball import scorebug
from vball.paths import DATASETS


def label(video: Path) -> dict:
    readings = scorebug.read_video(video)
    cap = cv2.VideoCapture(str(video))
    fps, n = cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    missed = []
    changes = scorebug.changes(readings, missed)
    return {"video": video.name, "fps": fps, "duration_s": round(n / fps, 1),
            "read_share": round(sum(s is not None for _, s in readings) / max(len(readings), 1), 3),
            "missed_points": sum(n for _, n in missed),
            "changes": [{"t": c.t, "team": c.team, "score": list(asdict(c.score).values()), "new_set": c.new_set}
                        for c in changes]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=Path, default=DATASETS / "watchdog" / "videos")
    ap.add_argument("--out", type=Path, default=DATASETS / "watchdog" / "labels")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if not scorebug.available():
        raise SystemExit("Tesseract is not installed (brew install tesseract)")
    args.out.mkdir(parents=True, exist_ok=True)
    for video in sorted(args.videos.glob("*.mp4")):
        dst = args.out / f"{video.stem}.json"
        if dst.exists() and not args.force:
            continue
        lab = label(video)
        dst.write_text(json.dumps(lab, indent=1))
        sets = [c for c in lab["changes"] if c["new_set"]]
        print(f"{video.stem}: {len(lab['changes'])} points ({lab['missed_points']} missed), {len(sets)} sets, "
              f"read {lab['read_share']:.0%}", flush=True)


if __name__ == "__main__":
    main()
