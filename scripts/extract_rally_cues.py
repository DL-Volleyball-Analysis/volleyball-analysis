"""Rally cues from a full match video, sampled at `--rate` per second, from the project's own models.

Per sample (CSV row): time; court: mean confidence of the 10 floor keypoints and whether a plausible court is
fitted (a wide view of the court vs a close-up or replay); players: number of player boxes and their mean motion
since the previous sample (box centre, nearest neighbour, in box heights); ball: share of the frames since the
previous sample with a VballNet detection and the median detected speed (image widths per second). Frames are read
as a stream, so a full match never sits in memory. `<out>.json` next to the CSV holds the video's fps and frame
count (labels are in frames).

  python scripts/extract_rally_cues.py --video match.mp4 --out cues.csv [--rate 5] [--device 0]
"""
import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

from vball.ball_detect import SEQ, VballNet
from vball.court_keypoints import detect as detect_court
from vball.court_keypoints import fit_homography
from vball.paths import BALL_MODELS, MODELS

COLUMNS = ["t", "court_conf", "court_ok", "players", "player_motion", "ball_seen", "ball_speed"]


def player_motion(prev: np.ndarray, cur: np.ndarray) -> float:
    """Mean distance from each current box centre to the nearest previous one, in box heights (0 if either is empty).
    Boxes: (n, 4) x1, y1, x2, y2."""
    if not len(prev) or not len(cur):
        return 0.0
    c0 = np.c_[(prev[:, 0] + prev[:, 2]) / 2, (prev[:, 1] + prev[:, 3]) / 2]
    c1 = np.c_[(cur[:, 0] + cur[:, 2]) / 2, (cur[:, 1] + cur[:, 3]) / 2]
    d = np.linalg.norm(c1[:, None] - c0[None], axis=2).min(axis=1)
    h = np.maximum(cur[:, 3] - cur[:, 1], 1.0)
    return float(np.mean(d / h))


def ball_summary(points: list, fps: float, width: int) -> tuple[float, float]:
    """points: per frame (x, y) or None since the previous sample -> (share seen, median speed in widths / s)."""
    if not points:
        return 0.0, 0.0
    seen = [p for p in points if p is not None]
    speeds = [np.hypot(b[0] - a[0], b[1] - a[1]) * fps / width
              for a, b in zip(points[:-1], points[1:]) if a is not None and b is not None]
    return len(seen) / len(points), float(np.median(speeds)) if speeds else 0.0


def extract(video: Path, out: Path, rate: float = 5.0, device=None) -> int:
    from ultralytics import YOLO
    court = YOLO(str(MODELS / "court_kpt_broadcast.pt"))
    court_sz = int((court.overrides or {}).get("imgsz", 1280))
    players = YOLO(str(MODELS / "player_yolo26s_sportsmot.pt"))
    ball = VballNet(BALL_MODELS["v4c"])
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    step = max(1, int(round(fps / rate)))
    rows, prev_boxes, ball_pts, buf, i = [], np.zeros((0, 4)), [], [], 0

    def flush_ball():
        nonlocal buf
        if buf:
            for cs in ball.candidates(buf):
                c = max(cs, key=lambda c: c.score) if cs else None
                ball_pts.append(None if c is None else (c.x, c.y))
            buf = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        buf.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if len(buf) == SEQ:
            flush_ball()
        if i % step == 0:
            flush_ball()
            kp = detect_court(court, frame, court_sz)
            size = (frame.shape[1], frame.shape[0])
            r = players(frame, imgsz=960, conf=0.25, verbose=False, device=device)[0]
            boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else np.zeros((0, 4))
            seen, speed = ball_summary(ball_pts, fps, width)
            rows.append([round(i / fps, 3), round(float(kp[:10, 2].mean()), 4), int(fit_homography(kp, size) is not None),
                         len(boxes), round(player_motion(prev_boxes, boxes), 4), round(seen, 3), round(speed, 4)])
            prev_boxes, ball_pts = boxes, []
        i += 1
    cap.release()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    out.with_suffix(".json").write_text(json.dumps({"fps": fps, "frames": i, "video": video.name}))
    return len(rows)


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
