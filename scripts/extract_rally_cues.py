"""Rally cues from a full match video, sampled at `--rate` per second, from the project's own models.

The cues are vball.rally_cues (court, players, ball at `--rate` samples per second), the same the pipeline's rallies
stage computes. `<out>.json` next to the CSV holds the video's fps and frame count (labels are in frames).

  python scripts/extract_rally_cues.py --video match.mp4 --out cues.csv [--rate 5] [--device 0]
"""

import argparse
import json
from pathlib import Path

from vball.rally_cues import cues


def extract(video: Path, out: Path, rate: float = 5.0, device=None) -> int:
    df, fps, frames = cues(video, rate, device)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    out.with_suffix(".json").write_text(json.dumps({"fps": fps, "frames": frames, "video": video.name}))
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rate", type=float, default=5.0)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()
    print(args.video, extract(Path(args.video), Path(args.out), args.rate, args.device), "samples")


if __name__ == "__main__":
    main()
