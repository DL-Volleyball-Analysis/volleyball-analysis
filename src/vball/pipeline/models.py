"""Adapters to the trained models (ultralytics weights loaded here and nowhere else in the pipeline).

Every function here is what a test replaces with a fake: stages call them as `models.NAME`.
"""

from pathlib import Path

import numpy as np

from vball import actions, players
from vball.court_keypoints import detect as detect_keypoints

from . import config


def court_detector(weights: Path):
    """frame -> 14 x (x, y, conf) with one court model, at the size it was trained at.
    Tests replace this function with a fake detector."""
    from ultralytics import YOLO

    model = YOLO(str(weights))
    imgsz = int((getattr(model, "overrides", {}) or {}).get("imgsz", 640))
    return lambda frame: detect_keypoints(model, frame, imgsz)


def person_counts(weights: str, frames: list, imgsz: int) -> list[int]:
    """People per frame found by a detector (tests replace this function with a fake)."""
    from ultralytics import YOLO

    model = YOLO(weights)
    return [
        len(model(f, imgsz=imgsz, conf=config.PLAYER_CFG.conf, classes=[players.PERSON], verbose=False)[0].boxes)
        for f in frames
    ]


def action_detector():
    """frame -> rows of (action, conf, x1, y1, x2, y2). Tests replace this function with a fake."""
    from ultralytics import YOLO

    model = YOLO(str(config.ACTION_MODEL))

    def detect(frame):
        r = model(frame, imgsz=640, conf=actions.ActionConfig().min_conf, verbose=False)[0]
        return [
            (r.names[int(c)], float(p), *map(float, b))
            for c, p, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())
        ]

    return detect


def person_classifier():
    """-> (class names, crops -> (n, classes) probabilities). Tests replace this function with a fake."""
    from ultralytics import YOLO

    model = YOLO(str(config.PERSON_MODEL))
    names = [model.names[i] for i in range(len(model.names))]

    def classify(crops):
        if not crops:
            return np.zeros((0, len(names)))
        return np.stack([r.probs.data.cpu().numpy() for r in model(crops, imgsz=224, verbose=False)])

    return names, classify


def digit_detector():
    """player crop -> rows of (digit, conf, x1, y1, x2, y2). Tests replace this function with a fake."""
    from ultralytics import YOLO

    model = YOLO(str(config.JERSEY_MODEL))

    def detect(crop):
        r = model(crop, imgsz=320, conf=0.25, verbose=False)[0]
        return [
            (int(r.names[int(c)]), float(p), *map(float, b))
            for c, p, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())
        ]

    return detect


def rally_cues(video: Path, tick):
    """Cues at 5 Hz (vball.rally_cues). Tests replace this function with a fake."""
    from vball.rally_cues import cues

    df, _, _ = cues(video, tick=tick)
    return df


def rally_quick_check(video: Path):
    """Cues on 30 frames spread over the video (vball.rally_cues.quick_check). Tests replace this function."""
    from vball.rally_cues import quick_check

    return quick_check(video)
