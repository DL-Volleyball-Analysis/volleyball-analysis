"""Player action events: action detections assigned to player tracks and merged over time.

The action model (YOLOv11m, classes block, receive, serve, set, spike) runs on sampled full frames and returns
boxes around the acting player. Each box goes to the player track whose box overlaps it most (IoU at least
`min_iou`); a box that overlaps no track is kept without a player. Consecutive detections of one action by one
track, at most `max_gap` samples apart, become one event with its first and last frame and peak confidence;
events whose peak is below `min_peak` are dropped (the capstone's threshold). Detections without a player merge
only while their boxes keep overlapping, so two unassigned players are not joined into one event.

Detections: rows of (frame, action, conf, x1, y1, x2, y2) in pixels. Tracks: the players stage table
(`vball.players.COLUMNS`), one box per track and frame.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

ACTIONS = ("block", "receive", "serve", "set", "spike")  # the model's class order
DETECTION_COLUMNS = ["frame", "action", "conf", "x1", "y1", "x2", "y2"]


@dataclass(frozen=True)
class ActionConfig:
    min_iou: float = 0.3   # action box vs player box
    max_gap: int = 3       # samples; a longer pause starts a new event
    min_peak: float = 0.6  # events below this peak confidence are dropped
    min_conf: float = 0.25  # detections below this are ignored before merging


@dataclass
class Event:
    action: str
    track_id: int | None
    start_frame: int
    end_frame: int
    peak_conf: float
    samples: int


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU of one box a (4,) against boxes b (N, 4), as x1, y1, x2, y2."""
    x1, y1 = np.maximum(a[0], b[:, 0]), np.maximum(a[1], b[:, 1])
    x2, y2 = np.minimum(a[2], b[:, 2]), np.minimum(a[3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]) - inter
    return np.where(union > 0, inter / np.where(union > 0, union, 1), 0.0)


def assign(detections: pd.DataFrame, tracks: pd.DataFrame, cfg: ActionConfig = ActionConfig()) -> pd.DataFrame:
    """The detections with a track_id column (<NA> when no track box overlaps enough)."""
    det = detections[detections["conf"] >= cfg.min_conf].copy()
    by_frame = {f: g for f, g in tracks.groupby("frame")} if len(tracks) else {}
    ids = []
    for row in det.itertuples():
        g = by_frame.get(row.frame)
        if g is None:
            ids.append(pd.NA)
            continue
        o = iou(np.array([row.x1, row.y1, row.x2, row.y2]), g[["x1", "y1", "x2", "y2"]].to_numpy(float))
        k = int(np.argmax(o))
        ids.append(int(g["track_id"].iloc[k]) if o[k] >= cfg.min_iou else pd.NA)
    det["track_id"] = pd.array(ids, dtype="Int64")
    return det


def merge(assigned: pd.DataFrame, sample_step: int, cfg: ActionConfig = ActionConfig()) -> list[Event]:
    """Events from assigned detections. sample_step: frames between action samples."""
    gap = cfg.max_gap * sample_step
    open_: list[tuple[Event, np.ndarray]] = []  # events still accepting detections, with their last box
    done: list[Event] = []
    for row in assigned.sort_values(["frame", "conf"], ascending=[True, False]).itertuples():
        tid = None if pd.isna(row.track_id) else int(row.track_id)
        box = np.array([row.x1, row.y1, row.x2, row.y2], float)
        done.extend(ev for ev, _ in open_ if row.frame - ev.end_frame > gap)  # paused too long: closed
        open_ = [(ev, last) for ev, last in open_ if row.frame - ev.end_frame <= gap]
        match = None
        for k, (ev, last) in enumerate(open_):
            if ev.action != row.action or ev.track_id != tid or ev.end_frame == row.frame:
                continue
            if tid is None and iou(box, last[None])[0] <= 0:
                continue  # unassigned: only the same place on screen continues an event
            match = k
            break
        if match is None:
            open_.append((Event(row.action, tid, int(row.frame), int(row.frame), float(row.conf), 1), box))
        else:
            ev, _ = open_[match]
            ev.end_frame, ev.peak_conf, ev.samples = int(row.frame), max(ev.peak_conf, float(row.conf)), ev.samples + 1
            open_[match] = (ev, box)
    done.extend(ev for ev, _ in open_)
    return sorted((e for e in done if e.peak_conf >= cfg.min_peak), key=lambda e: (e.start_frame, e.action))


def events(detections: pd.DataFrame, tracks: pd.DataFrame, sample_step: int,
           cfg: ActionConfig = ActionConfig()) -> list[Event]:
    return merge(assign(detections, tracks, cfg), sample_step, cfg)
