"""Players: detection, tracking, court positions and roles."""

from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball import players, teams

from .. import config, models, results


def choose_player_detector(video: Path, n_frames: int, samples: int = 8) -> tuple[players.TrackerConfig, dict]:
    """The player-only detector unless it misses most people on this footage (vball.players.prefer_generalist)."""
    if not Path(config.GENERAL_PLAYER_MODEL).exists() or not Path(config.PLAYER_CFG.model).exists() or n_frames < 1:
        return config.PLAYER_CFG, {"model": Path(config.PLAYER_CFG.model).stem, "reason": "default"}
    cap, picks = cv2.VideoCapture(str(video)), []
    for f in np.linspace(0, n_frames - 1, samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, frame = cap.read()
        if ok:
            picks.append(frame)
    cap.release()
    spec = models.person_counts(config.PLAYER_CFG.model, picks, config.PLAYER_CFG.imgsz)
    gen = models.person_counts(str(config.GENERAL_PLAYER_MODEL), picks, config.PLAYER_CFG.imgsz)
    info = {
        "player_only_median": float(np.median(spec)) if spec else 0.0,
        "general_median": float(np.median(gen)) if gen else 0.0,
    }
    if spec and gen and players.prefer_generalist(spec, gen):
        cfg = replace(config.PLAYER_CFG, model=str(config.GENERAL_PLAYER_MODEL))
        return cfg, {
            **info,
            "model": Path(cfg.model).stem,
            "reason": "the player-only detector found too few people on this footage",
        }
    return config.PLAYER_CFG, {**info, "model": Path(config.PLAYER_CFG.model).stem, "reason": "player-only detector"}


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    n = prev["decode"].get("frames") or 0
    fps = prev["decode"].get("fps") or 30.0

    def frames():
        cap = cv2.VideoCapture(str(video))
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
            i += 1
            if n and i % 50 == 0:
                tick(i / n)
        cap.release()

    cfg, choice = choose_player_detector(video, n)
    df = players.track_frames(frames(), fps, cfg)
    size = (prev["decode"].get("width"), prev["decode"].get("height"))
    df = players.place_on_court(df, results.court_homography_at(prev.get("court"), size))
    df = players.roles(df, team_assignments(video, df))
    df.to_csv(out / "players.csv.gz", index=False, float_format="%.2f")
    placed = bool(df["placed"].any()) if len(df) else False
    others = df.loc[df["role"] == "other", "track_id"].nunique() if len(df) else 0
    res = {
        "status": "done",
        "model": cfg.label(),
        "detector_choice": choice,
        "tracks": int(df["track_id"].nunique()) if len(df) else 0,
        "rows": int(len(df)),
        "placed": placed,
        "other_tracks": int(others),
    }
    if not placed:
        res["message"] = "The court was not found, so everyone in view is kept and no court positions are given."
    return res


def team_assignments(video: Path, df: pd.DataFrame, per_track: int = 10) -> dict:
    """vball.teams on torso colours of up to `per_track` detected (not interpolated) boxes per track."""
    seen = df[~df["interpolated"].astype(bool)] if len(df) else df
    if not len(seen):
        return {}
    picks: dict[int, list] = {}
    for tid, g in seen.groupby("track_id"):
        for r in g.iloc[np.linspace(0, len(g) - 1, min(per_track, len(g))).astype(int)].itertuples():
            picks.setdefault(int(r.frame), []).append((int(tid), (r.x1, r.y1, r.x2, r.y2)))
    hists: dict[int, list] = {}
    cap, i, last = cv2.VideoCapture(str(video)), 0, max(picks)
    while i <= last:
        ok, frame = cap.read() if i in picks else (cap.grab(), None)
        if not ok:
            break
        if frame is not None:  # decoded only for picked frames
            for tid, box in picks[i]:
                crop = teams.torso_crop(frame, box)
                if crop is not None and crop.size:
                    hists.setdefault(tid, []).append(teams.colour_hist(crop))
        i += 1
    cap.release()
    n_frames = df["frame"].nunique()
    coverage = (df.groupby("track_id")["frame"].nunique() / max(n_frames, 1)).to_dict()
    return teams.assign({t: np.array(h) for t, h in hists.items()}, coverage)
