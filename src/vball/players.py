"""Player detection and tracking.

Detect and track people at a reduced rate (default 10 fps), then interpolate each track's box
linearly between sampled frames, so every frame of the video has boxes. The detector + tracker is
ultralytics' YOLO person detector with its built-in tracker (BoT-SORT or ByteTrack); tests inject a
fake one through `step`.

`track_frames` output: DataFrame[frame, track_id, x1, y1, x2, y2, conf, interpolated] in original image
pixels. `place_on_court` then adds the court position of each box's feet (bottom-centre) from the frame's
court mapping and drops people outside the court plus margins (referees, bench, crowd):

  court_x, court_y  metres in the court frame of vball.court (NaN without a mapping)
  side              "a" (x < 9 m) / "b" side of the net, "" without a mapping
  placed            True when the frame had a court mapping (position and filter applied)

Stored by the web app as players.csv.gz with these columns. Teams are not assigned here: which team
plays on which side changes between sets and belongs to rally scoring.
"""
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .court import LENGTH, WIDTH, side_of_net, to_court

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


SIDE_MARGIN_M = 3.0  # beyond the sidelines (free zone)
END_MARGIN_M = 7.0   # behind the end lines, where servers stand


def place_on_court(df: pd.DataFrame, homography_at: Callable[[int], np.ndarray | None],
                   side_margin: float = SIDE_MARGIN_M, end_margin: float = END_MARGIN_M) -> pd.DataFrame:
    """Court position of each box's feet and the on-court filter.

    homography_at(frame) gives the court -> image homography of that frame, or None when the frame has
    no court mapping: such rows are kept unfiltered with `placed` False and no position."""
    out = df.copy()
    out["court_x"], out["court_y"], out["side"], out["placed"] = np.nan, np.nan, "", False
    keep = np.ones(len(out), bool)
    for frame, idx in out.groupby("frame").groups.items():
        H = homography_at(int(frame))
        if H is None:
            continue
        rows = out.loc[idx]
        feet = np.column_stack([(rows["x1"] + rows["x2"]) / 2, rows["y2"]])
        xy = to_court(H, feet)
        out.loc[idx, "court_x"], out.loc[idx, "court_y"] = xy[:, 0], xy[:, 1]
        out.loc[idx, "side"] = [side_of_net(x) for x in xy[:, 0]]
        out.loc[idx, "placed"] = True
        inside = ((xy[:, 0] >= -end_margin) & (xy[:, 0] <= LENGTH + end_margin)
                  & (xy[:, 1] >= -side_margin) & (xy[:, 1] <= WIDTH + side_margin))
        keep[out.index.get_indexer(idx)] = inside
    return out[keep].reset_index(drop=True)
