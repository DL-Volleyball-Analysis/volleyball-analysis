"""Rallies: play / no play from the system's cues, with the model for the kind of footage.

Still end-line cameras (camera shots that do not move and have an ok court) use the fixed-camera model on cues from
the earlier stages' results (`vball.rally_cues.shot_cues`, the same code that made its training data); other footage
uses the broadcast model on its own cues, after a quick check that it looks like broadcast footage.
"""

from pathlib import Path

import pandas as pd

from vball import court_registration, players
from vball import rallies as vrallies
from vball.manifest import usable
from vball.rally_cues import shot_cues

from .. import config, models, results

MISSING = "The rally model is missing or is not the expected version (models/manifest.json)."


def still_courts(prev: dict, out: Path) -> bool:
    """Every camera shot with an ok court is filmed by a still camera (and there is at least one)."""
    meta, court = prev.get("decode") or {}, prev.get("court") or {}
    size = (int(meta.get("width") or 0), int(meta.get("height") or 0))
    motion = results.motion_of(out)
    ok = [s for s in court.get("shots", []) if s.get("status") == "ok" and s.get("samples")]
    return bool(ok) and all(court_registration.still(motion, s["start_frame"], s["end_frame"], size) for s in ok)


def fixed_camera(video: Path, out: Path, prev: dict) -> dict:
    """Rallies on a still end-line camera with the fixed-camera model."""
    meta = prev["decode"]
    fps, n, size = meta.get("fps") or 30.0, meta.get("frames") or 0, (meta.get("width"), meta.get("height"))
    people_csv = out / "people.csv.gz"
    if people_csv.exists():
        people = pd.read_csv(people_csv)
    else:
        people = models.people_boxes(video, n, players.sample_every(fps, config.PEOPLE_FPS))
        people.to_csv(people_csv, index=False)  # full precision: a rerun reads exactly what the first run used
    cues = shot_cues(prev["court"], pd.read_csv(out / "ball.csv"), people, fps, size)
    found = vrallies.detect(vrallies.load_model(config.FIXED_RALLY_MODEL), cues) if len(cues) else []
    return rows_result(found, config.FIXED_RALLY_MODEL, "still end-line camera")


def broadcast(video: Path, tick) -> dict:
    """Rallies on broadcast-like footage with the broadcast model."""
    quick = models.rally_quick_check(video)  # out-of-training footage is told from a few frames (speed-up-analysis)
    why = vrallies.outside_training(quick) if quick is not None and len(quick) else None
    cues = None
    if not why:
        cues = models.rally_cues(video, tick)
        why = vrallies.outside_training(cues) if cues is not None else None
    if why:
        return {
            "status": "unavailable",
            "message": f"Rallies cannot be told on this footage: {why}. The rally models were trained on broadcast "
            "views and on still end-line cameras with the court found.",
        }
    return rows_result(vrallies.detect(vrallies.load_model(config.RALLY_MODEL), cues), config.RALLY_MODEL, "broadcast")


def rows_result(found: list, model: Path, footage: str) -> dict:
    rows = [{"start_s": round(a, 2), "end_s": round(b, 2), "confidence": round(c, 3)} for a, b, c in found]
    res = {"status": "done", "model": model.name, "footage": footage, "count": len(rows), "rallies": rows}
    if not rows:
        res["message"] = "No rally found: the court, players and ball never looked like play."
    return res


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    """Rallies (start, end, confidence) with the model for this footage (docs/results/rallies.md). Winners stay a user
    decision until landing calls exist; the worker writes the rallies to the database."""
    if still_courts(prev, out):
        if not usable(config.FIXED_RALLY_MODEL):
            return {"status": "unavailable", "message": MISSING}
        return fixed_camera(video, out, prev)
    if not usable(config.RALLY_MODEL):
        return {"status": "unavailable", "message": MISSING}
    return broadcast(video, tick)
