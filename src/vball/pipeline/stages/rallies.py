"""Rallies: play / no play from the system's cues with the trained rally model."""

from pathlib import Path

from vball import rallies as vrallies
from vball.manifest import usable

from .. import config, models


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    """Rallies (start, end, confidence) from the system's cues with the trained rally model (docs/results/rallies.md).
    Winners stay a user decision until landing calls exist; the worker writes the rallies to the database."""
    if not usable(config.RALLY_MODEL):
        return {
            "status": "unavailable",
            "message": "The rally model is missing or is not the expected version (models/manifest.json).",
        }
    quick = models.rally_quick_check(video)  # out-of-training footage is told from a few frames (speed-up-analysis)
    why = vrallies.outside_training(quick) if quick is not None and len(quick) else None
    cues = None
    if not why:
        cues = models.rally_cues(video, tick)
        why = vrallies.outside_training(cues) if cues is not None else None
    if why:
        return {
            "status": "unavailable",
            "message": f"Rallies cannot be told on this footage: {why}. The rally model was trained on broadcast "
            "views with the court in view.",
        }
    found = vrallies.detect(vrallies.load_model(config.RALLY_MODEL), cues)
    rows = [{"start_s": round(a, 2), "end_s": round(b, 2), "confidence": round(c, 3)} for a, b, c in found]
    res = {"status": "done", "model": config.RALLY_MODEL.name, "count": len(rows), "rallies": rows}
    if not rows:
        res["message"] = "No rally found: the court, players and ball never looked like play."
    return res
