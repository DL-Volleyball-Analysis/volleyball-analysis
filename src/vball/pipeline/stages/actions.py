"""Actions: action events and shirt numbers per player track."""

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball import actions, actors, jersey, players

from .. import config, models, results


def player_crop(frame: np.ndarray, row) -> np.ndarray | None:
    """Upper 60% of a player box (numbers are on the back and chest), None when too small to read."""
    x1, y1, x2, y2 = (int(round(v)) for v in (row.x1, row.y1, row.x2, row.y2))
    h, w = frame.shape[:2]
    x1, x2, y1 = max(0, x1), min(w, x2), max(0, y1)
    y2 = min(h, y1 + int(0.6 * (y2 - y1)))
    if x2 - x1 < 16 or y2 - y1 < 24:
        return None
    return frame[y1:y2, x1:x2]


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    """Action events per player track (vball.actions) and shirt numbers per track (vball.jersey). Block, receive, set
    and spike come from the per-player classifier weighted by the ball's position (vball.actors) when it is installed,
    serves from the action detector; without the classifier every action comes from the detector."""
    if not config.ACTION_MODEL.exists() and not config.PERSON_MODEL.exists():
        return {"status": "unavailable", "message": "The action model is not installed."}
    tracks_csv = out / "players.csv.gz"
    tracks = pd.read_csv(tracks_csv) if tracks_csv.exists() else pd.DataFrame(columns=players.COLUMNS)
    n, fps = prev["decode"].get("frames") or 0, prev["decode"].get("fps") or 30.0
    a_step, j_step = players.sample_every(fps, config.ACTION_FPS), players.sample_every(fps, config.JERSEY_FPS)
    detect = models.action_detector() if config.ACTION_MODEL.exists() else None
    person = models.person_classifier() if config.PERSON_MODEL.exists() else None
    # with the classifier the detector only gives serves, which last over a second: it runs at config.SERVE_FPS
    d_step = players.sample_every(fps, config.SERVE_FPS) if person is not None else a_step
    serves = []
    read = models.digit_detector() if config.JERSEY_MODEL.exists() else None
    if "role" in tracks:
        tracks = tracks[tracks["role"] == "player"]  # officials and staff are not given actions or numbers
    seen = tracks[~tracks["interpolated"].astype(bool)] if len(tracks) else tracks
    by_frame = {f: g for f, g in seen.groupby("frame")} if read and len(seen) else {}
    boxes_at = {f: g for f, g in tracks.groupby("frame")} if person and len(tracks) else {}
    balls = results.ball_points(out) if person else {}
    rows, readings = [], {}
    cap, i = cv2.VideoCapture(str(video)), 0
    while True:
        wanted = i % a_step == 0 or i % d_step == 0 or (read is not None and i % j_step == 0 and i in by_frame)
        ok, frame = cap.read() if wanted else (cap.grab(), None)  # decode only the frames that are used
        if not ok:
            break
        if wanted:
            if detect is not None and i % d_step == 0:
                if person is None:
                    rows.extend((i, *d) for d in detect(frame))
                else:  # with the classifier, the detector only contributes serves
                    serves.extend((i, *d) for d in detect(frame) if d[0] == "serve")
            if i % a_step == 0:
                if person is not None and i in boxes_at:
                    g = boxes_at[i]
                    boxes = g[["x1", "y1", "x2", "y2"]].to_numpy(float)
                    crops = [actors.person_crop(frame, b) for b in boxes]
                    keep = [k for k, c in enumerate(crops) if c is not None]
                    if keep:
                        names, classify = person
                        probs = classify([crops[k] for k in keep])
                        rows.extend(
                            actors.classifier_rows(
                                i,
                                boxes[keep],
                                probs,
                                names,
                                balls.get(i),
                                config.BALL_PRIOR,
                                min_conf=actions.ActionConfig().min_conf,
                            )
                        )
            if read is not None and i % j_step == 0:
                for row in by_frame.get(i, pd.DataFrame()).itertuples():
                    crop = player_crop(frame, row)
                    if crop is not None:
                        readings.setdefault(int(row.track_id), []).append((i, jersey.reading(read(crop))))
        i += 1
        if n and i % 50 == 0:
            tick(i / n)
    cap.release()
    evs = actions.events(pd.DataFrame(rows, columns=actions.DETECTION_COLUMNS), tracks, a_step)
    if serves:  # merged on their own sampling step, so the sparser samples are not split into separate events
        evs = sorted(
            evs + actions.events(pd.DataFrame(serves, columns=actions.DETECTION_COLUMNS), tracks, d_step),
            key=lambda e: e.start_frame,
        )
    numbers = {tid: jersey.vote([x for _, x in r]) for tid, r in readings.items()}
    # time-local numbers: a label follows a tracker identity switch instead of keeping the old number
    window = int(round(fps))  # +-1 s of readings
    segs = {tid: jersey.segments([f for f, _ in r], [x for _, x in r], window) for tid, r in readings.items()}
    data = {
        "events": [
            {
                "action": e.action,
                "track_id": e.track_id,
                "start_frame": e.start_frame,
                "end_frame": e.end_frame,
                "start_s": round(e.start_frame / fps, 3),
                "end_s": round(e.end_frame / fps, 3),
                "peak_conf": round(e.peak_conf, 3),
                "samples": e.samples,
            }
            for e in evs
        ],
        "numbers": {
            str(tid): {"number": v.number, "share": round(v.share, 3), "readings": v.readings}
            for tid, v in sorted(numbers.items())
        },
        "segments": {str(tid): [list(s) for s in sg] for tid, sg in sorted(segs.items())},
        "reach": j_step,  # a segment covers its reading frames plus this many frames on each side
    }
    (out / "action_events.json").write_text(json.dumps(data))  # actions.json is the stage result
    by_action = {a: sum(e.action == a for e in evs) for a in actions.ACTIONS}
    res = {
        "status": "done",
        "models": {
            "actions": config.ACTION_MODEL.name if detect else None,
            "person": config.PERSON_MODEL.name if person else None,
            "digits": config.JERSEY_MODEL.name if read else None,
        },
        "events": len(evs),
        "by_action": by_action,
        "numbered_tracks": sum(any(n is not None for _, _, n in sg) for sg in segs.values()),
    }
    if read is None:
        res["message"] = (
            "Shirt numbers are not read yet: the digit model is being retrained. Players are shown by tracking id."
        )
    return res
