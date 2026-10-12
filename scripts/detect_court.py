"""Court registration on one frame of each clip, with an overlay to check by eye.

Runs both court keypoint models (gym: court_kpt.pt, broadcast: court_kpt_broadcast.pt) on the frame, registers the
frame as a one-frame shot with each, and keeps the better one the way the pipeline does (vball.court_registration:
status, then floor-net consistency, then fit error). Only an ok court is drawn; a doubtful one is named, not drawn.
Writes outputs/court/detection/<clip>.jpg and <clip>.json.

  .venv/bin/python scripts/detect_court.py [--at 0.5]
"""

import argparse
import json
from pathlib import Path

import cv2

from vball import court, court_registration
from vball.court_keypoints import detect
from vball.paths import MODELS, OUTPUTS, VIDEOS

COURT_MODELS = {"gym": MODELS / "court_kpt.pt", "broadcast": MODELS / "court_kpt_broadcast.pt"}


def frame_at(video: Path, at: float):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) * at))
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def register_frame(models: dict, frame) -> dict:
    """The best one-frame registration over the models, as the pipeline picks per shot."""
    size = (frame.shape[1], frame.shape[0])
    one_frame = {**court_registration.CONFIG, "min_valid_samples": 1}  # a shot of one sample
    cands = {
        name: [court_registration.register_shot(0, 0, 1.0, size, lambda f, m=m: detect(m, frame), one_frame)]
        for name, m in models.items()
    }
    return court_registration.pick(cands)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", type=float, default=0.5, help="position in the clip (0-1)")
    args = ap.parse_args()
    from ultralytics import YOLO

    models = {name: YOLO(str(p)) for name, p in COURT_MODELS.items() if p.exists()}
    if not models:
        raise SystemExit(f"no court model in {MODELS}")
    out = OUTPUTS / "court" / "detection"
    out.mkdir(parents=True, exist_ok=True)
    for video in sorted(VIDEOS.glob("*.mp4")):
        frame = frame_at(video, args.at)
        if frame is None:
            continue
        shot = register_frame(models, frame)
        size = (frame.shape[1], frame.shape[0])
        H = court_registration.mapping_at({"shots": [shot]}, 0, size)
        img = court.draw(frame, H) if H is not None else frame.copy()
        cv2.putText(img, f"{shot['status']} ({shot['model']})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5)
        cv2.putText(
            img, f"{shot['status']} ({shot['model']})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2
        )
        cv2.imwrite(str(out / f"{video.stem}.jpg"), img)
        json.dump(
            {
                "status": shot["status"],
                "model": shot["model"],
                "error": shot["error"],
                "consistency": shot["consistency"],
                "H_court_to_image": None if H is None else H.tolist(),
            },
            open(out / f"{video.stem}.json", "w"),
            indent=1,
        )
        print(f"{video.stem:32} {shot['status']:13} model={shot['model']}")


if __name__ == "__main__":
    main()
