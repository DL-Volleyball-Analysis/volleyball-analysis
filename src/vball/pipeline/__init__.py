"""Staged analysis pipeline built on the `vball` package.

Each stage writes <results>/<stage>.json with its version and status. A rerun from stage S recomputes S and
everything after it; earlier stages are reused when their version still matches, so a new court model does not redo
ball tracking.

    from vball import pipeline
    out = pipeline.run(video, results_dir)          # {stage: result}

Layout: `stages/<name>.py` (one `run(video, out, prev, tick)` per stage), `config` (model files and rates),
`models` (adapters that load trained weights; tests replace them), `results` (the results folder).
"""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import config, models, results
from .results import corrected_court, load_stage, stage_file
from .stages import actions, ball, court, decode, events, players, rallies, trajectory

__all__ = [
    "config",
    "models",
    "results",
    "STAGES",
    "WEIGHTS",
    "FUNCS",
    "VERSIONS",
    "run",
    "load_stage",
    "stage_file",
    "corrected_court",
]

STAGES = ("decode", "court", "ball", "players", "actions", "trajectory", "events", "rallies")
# share of total pipeline time, for the progress bar
# Stage messages are shown to users as-is: write them for a coach, not a developer.
WEIGHTS = {
    "decode": 0.1,
    "court": 0.05,
    "ball": 0.3,
    "players": 0.33,
    "actions": 0.1,
    "trajectory": 0.02,
    "events": 0.05,
    "rallies": 0.05,
}
FUNCS = {
    "decode": decode.run,
    "court": court.run,
    "ball": ball.run,
    "players": players.run,
    "actions": actions.run,
    "trajectory": trajectory.run,
    "events": events.run,
    "rallies": rallies.run,
}
# players -4: the general detector where the player-only one misses players
VERSIONS = {
    "decode": "2",
    "court": "6",
    "ball": f"{config.BALL_MODEL}-1",
    "players": f"{config.PLAYER_CFG.label()}-4",
    "actions": "4",  # 3: per-player classifier + ball prior; 4: serves at SERVE_FPS
    "trajectory": "5",
    "events": "0.3",
    "rallies": "2",
}  # rallies 1: detected from cues; 2: quick check first


def run(
    video: Path,
    results_dir: Path,
    from_stage: str = "decode",
    on_progress: Callable[[str, float], None] = lambda stage, p: None,
    court_corrections: Callable[[], list[dict]] | None = None,
) -> dict:
    """Run the pipeline; returns {stage: result}. Raises on the first failing stage. Court corrections are read
    (court_corrections()) when the court stage is reached and overlaid on the court result later stages see, so
    a correction saved while a job waits or decodes is still applied."""
    if from_stage not in STAGES:
        raise ValueError(f"unknown stage {from_stage!r}; stages are {STAGES}")
    results_dir.mkdir(parents=True, exist_ok=True)
    start = STAGES.index(from_stage)
    done_weight, rerun, out = 0.0, False, {}
    for k, stage in enumerate(STAGES):
        cached = load_stage(results_dir, stage)
        rerun = rerun or k >= start or cached is None or cached.get("version") != VERSIONS[stage]
        if rerun:

            def tick(frac, stage=stage, base=done_weight):
                on_progress(stage, base + WEIGHTS[stage] * float(np.clip(frac, 0, 1)))

            tick(0)
            res = {"version": VERSIONS[stage], **FUNCS[stage](video, results_dir, out, tick)}
            stage_file(results_dir, stage).write_text(json.dumps(res))
            cached = res
        if stage == "court" and court_corrections is not None:
            cached = corrected_court(cached, out.get("decode"), court_corrections(), results_dir)
        out[stage] = cached
        done_weight += WEIGHTS[stage]
        on_progress(stage, done_weight)
    return out
