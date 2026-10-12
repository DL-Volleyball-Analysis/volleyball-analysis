"""Ball and player tracks, 3D flights and ball coverage over time windows."""
import json

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..deps import ball_table, db, players_table, video_or_404
from ..schemas import BallCoverage, BallWindow, Flight, FlightSample, Landing, NetCrossing, PlayerBox, PlayerWindow
from ..settings import RESULTS

router = APIRouter()


@router.get("/videos/{vid}/ball", response_model=BallWindow)
def ball_window(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """Ball positions between start and end seconds (whole video if end is omitted)."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "ball.csv"
    if not csv.exists():
        raise HTTPException(404, "ball tracking not run yet")
    df = ball_table(str(csv), csv.stat().st_mtime)
    fps = v["fps"] or 30.0
    lo, hi = int(start * fps), (int(end * fps) if end is not None else None)
    w = df[(df["frame"] >= lo) & ((df["frame"] <= hi) if hi is not None else True)]

    def col(c):
        a = w[c].to_numpy(float)
        return [None if np.isnan(x) else round(float(x), 1) for x in a]

    return BallWindow(fps=fps, frame=w["frame"].astype(int).tolist(), x=col("x"), y=col("y"))


@router.get("/videos/{vid}/players", response_model=PlayerWindow)
def player_window(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """Player boxes (image pixels) and court positions between start and end seconds."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "players.csv.gz"
    if not csv.exists():
        raise HTTPException(404, "player tracking not run yet")
    df = players_table(str(csv), csv.stat().st_mtime)
    fps = v["fps"] or 30.0
    lo, hi = int(start * fps), (int(end * fps) if end is not None else None)
    w = df[(df["frame"] >= lo) & ((df["frame"] <= hi) if hi is not None else True)]

    def num(x):
        return None if pd.isna(x) else round(float(x), 2)

    boxes = [PlayerBox(frame=int(r.frame), track_id=int(r.track_id), x1=num(r.x1), y1=num(r.y1), x2=num(r.x2),
                       y2=num(r.y2), interpolated=bool(r.interpolated), court_x=num(r.court_x),
                       court_y=num(r.court_y), side=(r.side if isinstance(r.side, str) and r.side else None),
                       team=(getattr(r, "team", "") if isinstance(getattr(r, "team", ""), str) and getattr(r, "team", "") else None),
                       role=getattr(r, "role", "player") if isinstance(getattr(r, "role", None), str) else "player")
             for r in w.itertuples(index=False)]
    return PlayerWindow(fps=fps, placed=bool(df["placed"].any()) if len(df) else False, boxes=boxes)


def flight_out(f: dict, fps: float, seen: np.ndarray, source: str) -> Flight:
    frames = np.arange(f["start_frame"], f["end_frame"] + 1)
    t = (frames - f["start_frame"]) / fps
    p0, v0 = np.array(f["p0"]), np.array(f["v0"])
    pos = p0 + np.outer(t, v0) + 0.5 * np.outer(t * t, [0, 0, -9.81])
    d = f["derived"]
    obs = [bool(seen[i]) if 0 <= i < len(seen) else False for i in frames]
    return Flight(start_s=frames[0] / fps, end_s=frames[-1] / fps, source=source, quality=f["quality"],
                  reasons=f["reasons"], fit_px=f.get("fit_px"), start_speed_mps=round(d["start_speed_mps"], 2),
                  apex_m=round(d["apex"]["height_m"], 2) if d.get("apex") else None,
                  net_crossing=NetCrossing(height_m=round(d["net_crossing"]["height_m"], 2), y_m=round(d["net_crossing"]["y_m"], 2))
                  if d.get("net_crossing") else None,
                  landing=Landing(x_m=round(d["landing"]["x_m"], 2), y_m=round(d["landing"]["y_m"], 2)) if d.get("landing") else None,
                  samples=[FlightSample(t=round(float(fr / fps), 3), x=round(float(p[0]), 3), y=round(float(p[1]), 3),
                                        z=round(float(p[2]), 3), observed=o) for fr, p, o in zip(frames, pos, obs)],
                  anchors=f.get("anchors", []), dropped=f.get("dropped", 0))


@router.get("/videos/{vid}/flights", response_model=list[Flight])
def flights(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """3D ball flights overlapping [start, end] seconds, with a court position for every frame.
    Videos with demo rallies get demo flights built from those rallies (source 'demo')."""
    from .. import demo
    v = video_or_404(vid)
    fps = v["fps"] or 30.0
    path = RESULTS / vid / "flights.json"
    stored = json.loads(path.read_text()) if path.exists() else None
    rows = db.list_rallies(vid)
    if stored:
        csv = RESULTS / vid / "ball.csv"
        seen = np.zeros(v["frames"] or 0, bool)
        if csv.exists():
            df = ball_table(str(csv), csv.stat().st_mtime)
            vis = df[(df["visible"] > 0) & (df["frame"] < len(seen))]["frame"].to_numpy(int)
            seen[vis] = True
        out = [flight_out(f, fps, seen, "model") for f in stored]
    elif any(r["source"] == "demo" for r in rows):
        out = [flight_out(f, fps, np.ones(v["frames"] or 0, bool), "demo") for f in demo.demo_flights(rows, fps)]
    elif path.exists():
        out = []
    else:
        raise HTTPException(404, "3D trajectories not computed yet")
    hi = end if end is not None else float("inf")
    return [f for f in out if f.end_s >= start and f.start_s <= hi]


MAX_COVERAGE_BINS = 2000


@router.get("/videos/{vid}/ball/coverage", response_model=BallCoverage)
def ball_coverage(vid: str, bins: int = Query(200, ge=1, le=MAX_COVERAGE_BINS)):
    """Where tracking found the ball, summarised over the whole video (for the timeline's ball lane)."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "ball.csv"
    if not csv.exists():
        raise HTTPException(404, "ball tracking not run yet")
    df = ball_table(str(csv), csv.stat().st_mtime)
    frames = int(df["frame"].max()) + 1 if len(df) else 0
    if frames == 0:
        return BallCoverage(duration_s=0, coverage=[0.0] * bins)
    which = np.minimum((df["frame"].to_numpy() * bins) // frames, bins - 1)
    seen = np.bincount(which, weights=df["visible"].to_numpy(float), minlength=bins)
    total = np.bincount(which, minlength=bins)
    cov = np.divide(seen, total, out=np.zeros(bins), where=total > 0)
    return BallCoverage(duration_s=frames / (v["fps"] or 30.0), coverage=[round(float(c), 3) for c in cov])
