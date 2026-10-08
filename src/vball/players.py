"""Player detection and tracking.

Detect and track people at a reduced rate (default 10 fps), then interpolate each track's box
linearly between sampled frames, so every frame of the video has boxes. The detector + tracker is
ultralytics' YOLO person detector with its built-in tracker (BoT-SORT or ByteTrack); tests inject a
fake one through `step`.

Output: DataFrame[frame, track_id, x1, y1, x2, y2, conf, interpolated] in original image pixels.
On-court filtering and court positions are added later from a court mapping (add-player-tracking).
"""
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd

COLUMNS = ["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"]
PERSON = 0  # COCO class id

# step(image) -> rows of (track_id, x1, y1, x2, y2, conf) for one sampled frame
Step = Callable[[np.ndarray], list[tuple[int, float, float, float, float, float]]]


@dataclass(frozen=True)
class TrackerConfig:
    model: str = "yolo26n.pt"
    imgsz: int = 960
    tracker: str = "botsort.yaml"  # or "bytetrack.yaml"
    det_fps: float = 10.0
    conf: float = 0.25

    def label(self) -> str:
        return f"{self.model.removesuffix('.pt')}_{self.imgsz}_{self.tracker.removesuffix('.yaml')}_{self.det_fps:g}fps"


def ultralytics_step(cfg: TrackerConfig) -> Step:
    """A stateful detector + tracker: call once per sampled frame, in order."""
    from ultralytics import YOLO

    model = YOLO(cfg.model)

    def step(image: np.ndarray):
        r = model.track(image, persist=True, tracker=cfg.tracker, classes=[PERSON], imgsz=cfg.imgsz,
                        conf=cfg.conf, verbose=False)[0]
        if r.boxes is None or r.boxes.id is None:
            return []
        ids = r.boxes.id.int().tolist()
        xyxy = r.boxes.xyxy.tolist()
        conf = r.boxes.conf.tolist()
        return [(i, *b, c) for i, b, c in zip(ids, xyxy, conf)]

    return step


def sample_every(src_fps: float, det_fps: float) -> int:
    """Run the detector on every k-th frame."""
    return max(1, round(src_fps / det_fps)) if det_fps > 0 else 1


def track_frames(frames: Iterable[np.ndarray], src_fps: float, cfg: TrackerConfig = TrackerConfig(),
                 step: Step | None = None) -> pd.DataFrame:
    """Detect + track on sampled frames (0-based frame numbers), then fill the frames in between."""
    step = step or ultralytics_step(cfg)
    k = sample_every(src_fps, cfg.det_fps)
    rows, n = [], 0
    for i, image in enumerate(frames):
        n = i + 1
        if i % k == 0:
            rows.extend((i, tid, x1, y1, x2, y2, c, False) for tid, x1, y1, x2, y2, c in step(image))
    sampled = pd.DataFrame(rows, columns=COLUMNS)
    return interpolate_tracks(sampled, n_frames=n) if k > 1 else sampled


def interpolate_tracks(df: pd.DataFrame, n_frames: int, max_gap: int | None = None) -> pd.DataFrame:
    """Linear box interpolation between a track's consecutive detections. Frames outside a track's
    first and last detection are not filled (no extrapolation); gaps longer than `max_gap` frames
    stay empty (the track was lost there)."""
    out = [df]
    for tid, g in df.sort_values("frame").groupby("track_id"):
        f = g["frame"].to_numpy()
        for a, b in zip(range(len(f) - 1), range(1, len(f))):
            gap = f[b] - f[a]
            if gap <= 1 or (max_gap is not None and gap > max_gap):
                continue
            t = (np.arange(f[a] + 1, f[b]) - f[a]) / gap
            box_a = g.iloc[a][["x1", "y1", "x2", "y2"]].to_numpy(float)
            box_b = g.iloc[b][["x1", "y1", "x2", "y2"]].to_numpy(float)
            boxes = box_a + t[:, None] * (box_b - box_a)
            conf = min(g.iloc[a]["conf"], g.iloc[b]["conf"])
            out.append(pd.DataFrame({
                "frame": np.arange(f[a] + 1, f[b]), "track_id": tid,
                "x1": boxes[:, 0], "y1": boxes[:, 1], "x2": boxes[:, 2], "y2": boxes[:, 3],
                "conf": conf, "interpolated": True,
            }))
    res = pd.concat(out, ignore_index=True)
    res = res[(res["frame"] >= 0) & (res["frame"] < n_frames)]
    return res.sort_values(["frame", "track_id"], ignore_index=True)[COLUMNS]
