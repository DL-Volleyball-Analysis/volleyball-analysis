"""Run court registration on one frame of each clip and save overlays.

Writes outputs/court_detection/<clip>.{jpg,json}.
Usage: .venv/bin/python scripts/detect_court.py [--method geometry] [--at 0.5]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball import court, court_geometry  # noqa: E402
from vball.paths import OUTPUTS, VIDEOS  # noqa: E402


def frame_at(video: Path, at: float):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) * at))
    ok, frame = cap.read()
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["geometry"], default="geometry")
    ap.add_argument("--at", type=float, default=0.5, help="position in the clip (0-1)")
    args = ap.parse_args()
    out = OUTPUTS / "court_detection"
    out.mkdir(parents=True, exist_ok=True)

    for video in sorted(VIDEOS.glob("*.mp4")):
        frame = frame_at(video, args.at)
        res = court_geometry.detect(frame)
        if res is None:
            print(f"{video.stem:32} no court found")
            continue
        cv2.imwrite(str(out / f"{video.stem}.jpg"), court.draw(frame, res["H"]))
        json.dump({"H_court_to_image": res["H"], "score": res["score"], "method": args.method},
                  open(out / f"{video.stem}.json", "w"), indent=1)
        print(f"{video.stem:32} score={res['score']:.1f}")


if __name__ == "__main__":
    main()
