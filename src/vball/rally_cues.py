"""Rally cues: what the system sees at 5 samples per second that separates play from the time between rallies.

Per sample: the mean confidence of the 10 court floor keypoints and whether a plausible court is fitted (a wide view
of the court vs a close-up or replay); the number of player boxes and their motion since the previous sample (box
centres, nearest neighbour, in box heights); the share of frames since the previous sample with a VballNet ball
detection and the median detected speed (image widths per second). Frames are read as a stream. Used by
scripts/extract_rally_cues.py (training data) and the pipeline's rallies stage, so both compute the same features.
"""
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from .ball_detect import SEQ, VballNet
from .court_keypoints import detect as detect_court
from .court_keypoints import fit_homography
from .paths import BALL_MODELS, MODELS

COLUMNS = ["t", "court_conf", "court_ok", "players", "player_motion", "ball_seen", "ball_speed"]
COURT_MODEL = MODELS / "court_kpt_broadcast.pt"
PLAYER_MODEL = MODELS / "player_yolo26s_sportsmot.pt"


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


def quick_check(video: Path, n: int = 30, device=None) -> pd.DataFrame:
    """Cues on n frames spread over the video (court model and player detector only; motion and ball columns 0):
    enough for `rallies.outside_training` to tell out-of-training footage without a full pass (change
    speed-up-analysis)."""
    from ultralytics import YOLO
    court = YOLO(str(COURT_MODEL))
    court_sz = int((court.overrides or {}).get("imgsz", 1280))
    players = YOLO(str(PLAYER_MODEL))
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rows = []
    for f in np.unique(np.linspace(0, max(total - 1, 0), n).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, frame = cap.read()
        if not ok:
            continue
        kp = detect_court(court, frame, court_sz)
        r = players(frame, imgsz=960, conf=0.25, verbose=False, device=device)[0]
        rows.append([round(f / fps, 3), round(float(kp[:10, 2].mean()), 4),
                     int(fit_homography(kp, (frame.shape[1], frame.shape[0])) is not None),
                     0 if r.boxes is None else len(r.boxes), 0.0, 0.0, 0.0])
    cap.release()
    return pd.DataFrame(rows, columns=COLUMNS)


def cues(video: Path, rate: float = 5.0, device=None, tick=lambda frac: None) -> tuple[pd.DataFrame, float, int]:
    """(cues per sample, fps, frames) for a video."""
    from ultralytics import YOLO
    court = YOLO(str(COURT_MODEL))
    court_sz = int((court.overrides or {}).get("imgsz", 1280))
    players = YOLO(str(PLAYER_MODEL))
    ball = VballNet(BALL_MODELS["v4c"])
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
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
            if total and i % (step * 25) == 0:
                tick(i / total)
        i += 1
    cap.release()
    return pd.DataFrame(rows, columns=COLUMNS), fps, i


# --- cues from the pipeline's own results (change label-rallies-from-score) -----------------------------------------
STAGE_COLUMNS = ["t", "ball_seen", "ball_speed", "ball_rise", "on_court", "both_sides", "behind_end", "player_speed",
                 "player_spread"]


def stage_cues(ball: pd.DataFrame, people: pd.DataFrame, fps: float, n_frames: int, image_size: tuple[int, int],
               H: np.ndarray | None, rate: float = 5.0, margin_m: float = 1.0) -> pd.DataFrame:
    """Rally cues at `rate` per second from results the pipeline already has, for a still camera whose court is known:

    ball (frame, visible, x, y; every frame): share of frames with a ball since the previous sample, its median speed
    (image widths / s) and its median upward speed (widths / s; a serve toss and sets go up);
    people (frame, x1, y1, x2, y2; any sampling): from the latest detected frame at or before each sample, the people
    standing on the court (H: court metres -> image; feet within `margin_m` of the court), the smaller of the two
    halves' counts (both teams in formation), people behind an end line (a server), their median speed in m/s against
    the previous detected frame (nearest neighbour) and the spread of their positions along the court (m).
    Without H every people cue is 0."""
    from .court import LENGTH, WIDTH, to_court
    w = float(image_size[0])
    step = max(1, int(round(fps / rate)))
    vis = np.zeros(n_frames, bool)
    xy = np.full((n_frames, 2), np.nan)
    if len(ball):
        b = ball[(ball["frame"] < n_frames) & (ball["visible"] > 0)]
        vis[b["frame"].to_numpy(int)] = True
        xy[b["frame"].to_numpy(int)] = b[["x", "y"]].to_numpy(float)
    groups = {int(f): g for f, g in people.groupby("frame")} if len(people) else {}
    pframes = np.array(sorted(groups))

    def court_points(f):
        g = groups[f]
        feet = np.c_[((g["x1"] + g["x2"]) / 2).to_numpy(float), g["y2"].to_numpy(float)]
        return to_court(H, feet) if H is not None and len(feet) else np.zeros((0, 2))

    rows, prev, last_speed = [], None, 0.0
    for i in range(0, n_frames, step):
        a = max(0, i - step + 1)
        seen = vis[a:i + 1]
        d = np.diff(xy[a:i + 1], axis=0) * fps / w
        ok = ~np.isnan(d).any(axis=1)
        speed = float(np.median(np.hypot(d[ok, 0], d[ok, 1]))) if ok.any() else 0.0
        rise = float(np.median(-d[ok, 1])) if ok.any() else 0.0
        on = behind = both = 0
        pspeed = spread = 0.0
        k = np.searchsorted(pframes, i, side="right") - 1
        if H is not None and k >= 0:
            f = int(pframes[k])
            c = court_points(f)
            inside_w = (c[:, 1] > -margin_m) & (c[:, 1] < WIDTH + margin_m)
            court = inside_w & (c[:, 0] > -margin_m) & (c[:, 0] < LENGTH + margin_m)
            behind = int((inside_w & ((c[:, 0] < -margin_m) & (c[:, 0] > -9) | (c[:, 0] > LENGTH + margin_m) & (c[:, 0] < LENGTH + 9))).sum())
            pts = c[court]
            on = len(pts)
            both = int(min((pts[:, 0] < 9).sum(), (pts[:, 0] >= 9).sum())) if on else 0
            spread = float(np.std(pts[:, 0])) if on > 1 else 0.0
            if prev is None or prev[0] != f:  # a new detected frame: its speed against the one before
                last_speed = 0.0
                if prev is not None and len(prev[1]) and on:
                    dist = np.linalg.norm(pts[:, None] - prev[1][None], axis=2).min(axis=1)
                    last_speed = float(np.median(dist) * fps / (f - prev[0]))
                prev = (f, pts)
            pspeed = last_speed  # samples between two detected frames keep the latest speed
        rows.append([round(i / fps, 3), round(float(seen.mean()) if len(seen) else 0.0, 3), round(speed, 4), round(rise, 4),
                     on, both, behind, round(pspeed, 3), round(spread, 3)])
    return pd.DataFrame(rows, columns=STAGE_COLUMNS)
