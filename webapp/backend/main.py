"""Volleyball analysis API.

Run: uvicorn --app-dir backend main:app --reload   (plus `python backend/worker.py` for analysis)
Heavy work never runs in this process: endpoints only queue jobs and read stage results.
"""
import asyncio
import json
import os
import shutil
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from vball.scoring import running_score
from vball import stats as vstats

import pipeline
from database import FINISHED, Database
from settings import DB_PATH, RESULTS, UPLOADS, VIDEO_SUFFIXES

app = FastAPI(title="Volleyball Analysis API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("VBALL_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
db = Database(DB_PATH)

Team = Literal["a", "b"]
Stage = Literal["decode", "court", "ball", "players", "actions", "trajectory", "events", "rallies"]


class Job(BaseModel):
    id: str
    video_id: str
    status: Literal["queued", "running", "done", "failed"]
    from_stage: Stage
    stage: Stage | None
    progress: float
    error: str | None
    created_at: str
    updated_at: str


class ScoreSummary(BaseModel):
    """Score after the last rally, for the library list."""
    set_no: int
    a: int
    b: int
    sets_a: int
    sets_b: int
    rallies: int
    corrected: int
    demo: bool


class Video(BaseModel):
    id: str
    name: str
    fps: float | None
    frames: int | None
    width: int | None
    height: int | None
    created_at: str
    job: Job | None
    score: ScoreSummary | None


class StageInfo(BaseModel):
    name: Stage
    status: Literal["pending", "done", "todo", "unavailable"]
    version: str | None = None
    message: str | None = None
    summary: dict = {}


class Score(BaseModel):
    set_no: int
    a: int
    b: int
    sets_a: int
    sets_b: int
    set_over: bool


class Rally(BaseModel):
    idx: int
    start_s: float
    end_s: float
    winner: Team | None
    winner_override: Team | None
    effective_winner: Team | None
    reason: str | None
    confidence: float | None
    landing_x: float | None
    landing_y: float | None
    source: Literal["model", "demo"]
    score: Score


class BallWindow(BaseModel):
    fps: float
    frame: list[int]
    x: list[float | None]   # image pixels, None when the ball is not detected
    y: list[float | None]


class BallCoverage(BaseModel):
    duration_s: float
    coverage: list[float]   # fraction of frames with a detection, per equal time bin


class PlayerBox(BaseModel):
    frame: int
    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    interpolated: bool
    court_x: float | None   # metres; None without a court mapping
    court_y: float | None
    side: Literal["a", "b"] | None
    team: Literal["a", "b"] | None = None             # by shirt colour; None when not trusted
    role: Literal["player", "other"] = "player"       # other: officials, staff, spectators (shown, not counted)


class PlayerWindow(BaseModel):
    fps: float
    placed: bool            # positions and the on-court filter were applied
    boxes: list[PlayerBox]


class FlightSample(BaseModel):
    t: float               # seconds in the video
    x: float               # court metres (vball.court frame, z up)
    y: float
    z: float
    observed: bool         # the ball was detected in this frame (else the position comes from the fit)


class NetCrossing(BaseModel):
    height_m: float
    y_m: float


class Landing(BaseModel):
    x_m: float
    y_m: float


class Flight(BaseModel):
    start_s: float
    end_s: float
    source: Literal["model", "demo"]
    quality: Literal["ok", "low"]
    reasons: list[str]
    fit_px: float | None
    start_speed_mps: float
    apex_m: float | None
    net_crossing: NetCrossing | None
    landing: Landing | None
    samples: list[FlightSample]
    anchors: list[Literal["start", "end"]] = []  # touches pulled toward a player's court position
    dropped: int = 0                              # detections left out as inconsistent with the flight


class ImportRequest(BaseModel):
    path: str


class JobRequest(BaseModel):
    from_stage: Stage = "decode"


class RallyPatch(BaseModel):
    winner: Team | None


def video_or_404(vid: str) -> dict:
    v = db.get_video(vid)
    if v is None:
        raise HTTPException(404, "video not found")
    return v


def effective_winners(rows: list[dict]) -> list[str | None]:
    """The user's correction wins over the model's winner."""
    return [r["winner_override"] or r["winner"] for r in rows]


def score_summary(vid: str) -> ScoreSummary | None:
    rows = db.list_rallies(vid)
    if not rows:
        return None
    last = running_score(effective_winners(rows))[-1]
    return ScoreSummary(set_no=last.set_no, a=last.a, b=last.b, sets_a=last.sets_a, sets_b=last.sets_b,
                        rallies=len(rows), corrected=sum(r["winner_override"] is not None for r in rows),
                        demo=any(r["source"] == "demo" for r in rows))


def video_out(v: dict) -> Video:
    return Video(**v, job=db.latest_job(v["id"]), score=score_summary(v["id"]))


def register(name: str, path: Path) -> Video:
    try:
        meta = pipeline.video_meta(path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    v = db.add_video(name, str(path), meta)
    db.add_job(v["id"], "decode")  # analysis starts right after upload
    return video_out(v)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/videos", response_model=list[Video])
def list_videos():
    return [video_out(v) for v in db.list_videos()]


@app.post("/videos", response_model=Video, status_code=201)
def upload_video(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(400, f"unsupported file type {suffix!r}")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f, length=8 << 20)
    try:
        return register(Path(file.filename).stem, dest)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise


@app.post("/videos/import", response_model=Video, status_code=201)
def import_video(req: ImportRequest):
    """Register a video already on this machine without copying it (local use)."""
    path = Path(req.path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
        raise HTTPException(400, "not a video file on this machine")
    return register(path.stem, path)


@app.get("/videos/{vid}", response_model=Video)
def get_video(vid: str):
    return video_out(video_or_404(vid))


@app.delete("/videos/{vid}", status_code=204)
def delete_video(vid: str):
    v = video_or_404(vid)
    db.delete_video(vid)
    path = Path(v["path"])
    if path.parent.resolve() == UPLOADS.resolve():  # never delete imported originals
        path.unlink(missing_ok=True)
    shutil.rmtree(RESULTS / vid, ignore_errors=True)


@app.get("/videos/{vid}/file")
def video_file(vid: str):
    """The video itself; FileResponse handles Range requests, so seeking works."""
    path = Path(video_or_404(vid)["path"])
    if not path.exists():
        raise HTTPException(404, "video file missing on disk")
    return FileResponse(path)


@app.post("/videos/{vid}/jobs", response_model=Job, status_code=201)
def start_job(vid: str, req: JobRequest):
    video_or_404(vid)
    if db.active_job(vid):
        raise HTTPException(409, "analysis already queued or running")
    return db.add_job(vid, req.from_stage)


@app.get("/videos/{vid}/jobs/latest", response_model=Job | None)
def latest_job(vid: str):
    video_or_404(vid)
    return db.latest_job(vid)


@app.get("/videos/{vid}/jobs/stream")
async def job_stream(vid: str, request: Request):
    """Server-sent events with the latest job state; closes when the job finishes."""
    video_or_404(vid)

    async def events():
        last = None
        while not await request.is_disconnected():
            job = db.latest_job(vid)
            payload = json.dumps(job)
            if payload != last:
                yield f"data: {payload}\n\n"
                last = payload
            if job is None or job["status"] in FINISHED:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.get("/videos/{vid}/stages", response_model=list[StageInfo])
def stages(vid: str):
    video_or_404(vid)
    out = []
    for name in pipeline.STAGES:
        res = pipeline.load_stage(RESULTS / vid, name)
        if res is None:
            out.append(StageInfo(name=name, status="pending"))
            continue
        res = dict(res)
        out.append(StageInfo(name=name, status=res.pop("status"), version=res.pop("version", None),
                             message=res.pop("message", None), summary=res))
    return out


@lru_cache(maxsize=8)
def _ball_track(csv: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(csv)


@app.get("/videos/{vid}/ball", response_model=BallWindow)
def ball_window(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """Ball positions between start and end seconds (whole video if end is omitted)."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "ball.csv"
    if not csv.exists():
        raise HTTPException(404, "ball tracking not run yet")
    df = _ball_track(str(csv), csv.stat().st_mtime)
    fps = v["fps"] or 30.0
    lo, hi = int(start * fps), (int(end * fps) if end is not None else None)
    w = df[(df["frame"] >= lo) & ((df["frame"] <= hi) if hi is not None else True)]

    def col(c):
        a = w[c].to_numpy(float)
        return [None if np.isnan(x) else round(float(x), 1) for x in a]

    return BallWindow(fps=fps, frame=w["frame"].astype(int).tolist(), x=col("x"), y=col("y"))


@lru_cache(maxsize=4)
def _players(csv: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(csv, keep_default_na=True)


@app.get("/videos/{vid}/players", response_model=PlayerWindow)
def player_window(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """Player boxes (image pixels) and court positions between start and end seconds."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "players.csv.gz"
    if not csv.exists():
        raise HTTPException(404, "player tracking not run yet")
    df = _players(str(csv), csv.stat().st_mtime)
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


@app.get("/videos/{vid}/flights", response_model=list[Flight])
def flights(vid: str, start: float = Query(0, ge=0), end: float | None = Query(None, ge=0)):
    """3D ball flights overlapping [start, end] seconds, with a court position for every frame.
    Videos with demo rallies get demo flights built from those rallies (source 'demo')."""
    import demo
    v = video_or_404(vid)
    fps = v["fps"] or 30.0
    path = RESULTS / vid / "flights.json"
    stored = json.loads(path.read_text()) if path.exists() else None
    rows = db.list_rallies(vid)
    if stored:
        csv = RESULTS / vid / "ball.csv"
        seen = np.zeros(v["frames"] or 0, bool)
        if csv.exists():
            df = _ball_track(str(csv), csv.stat().st_mtime)
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


@app.get("/videos/{vid}/ball/coverage", response_model=BallCoverage)
def ball_coverage(vid: str, bins: int = Query(200, ge=1, le=MAX_COVERAGE_BINS)):
    """Where tracking found the ball, summarised over the whole video (for the timeline's ball lane)."""
    v = video_or_404(vid)
    csv = RESULTS / vid / "ball.csv"
    if not csv.exists():
        raise HTTPException(404, "ball tracking not run yet")
    df = _ball_track(str(csv), csv.stat().st_mtime)
    frames = int(df["frame"].max()) + 1 if len(df) else 0
    if frames == 0:
        return BallCoverage(duration_s=0, coverage=[0.0] * bins)
    which = np.minimum((df["frame"].to_numpy() * bins) // frames, bins - 1)
    seen = np.bincount(which, weights=df["visible"].to_numpy(float), minlength=bins)
    total = np.bincount(which, minlength=bins)
    cov = np.divide(seen, total, out=np.zeros(bins), where=total > 0)
    return BallCoverage(duration_s=frames / (v["fps"] or 30.0), coverage=[round(float(c), 3) for c in cov])


def rallies_out(vid: str) -> list[Rally]:
    rows = db.list_rallies(vid)
    eff = effective_winners(rows)
    return [Rally(**r, effective_winner=w, score=Score(**s.__dict__))
            for r, w, s in zip(rows, eff, running_score(eff))]


@app.get("/videos/{vid}/rallies", response_model=list[Rally])
def list_rallies(vid: str):
    video_or_404(vid)
    return rallies_out(vid)


@app.patch("/videos/{vid}/rallies/{idx}", response_model=list[Rally])
def correct_rally(vid: str, idx: int, patch: RallyPatch):
    """Set (or clear, with null) the user's winner for one rally; returns all rallies with new scores."""
    video_or_404(vid)
    if not db.set_rally_override(vid, idx, patch.winner):
        raise HTTPException(404, "rally not found")
    return rallies_out(vid)


# --- player statistics: rosters, action tags, statistics (vball.stats) ---

TagKind = Literal["attack", "serve"]
Outcome = Literal["kill", "ace", "error", "in_play"]


class RosterPlayer(BaseModel):
    team: Team
    number: int
    name: str | None = None


class Roster(BaseModel):
    players: list[RosterPlayer]


class TagIn(BaseModel):
    time_s: float
    kind: TagKind
    team: Team
    number: int
    outcome: Outcome | None = None


class TagPatch(BaseModel):
    """Fields to change; `outcome: null` clears the user's outcome (back to inferred)."""
    time_s: float | None = None
    team: Team | None = None
    number: int | None = None
    outcome: Outcome | None = None


class TagOut(BaseModel):
    id: str
    time_s: float
    kind: TagKind
    team: Team
    number: int
    outcome: Outcome | None                 # set by the user
    effective_outcome: Literal["kill", "ace", "error", "in_play", "unknown", "outside"]
    inferred: bool                          # effective outcome comes from the rally winner / position
    rally_idx: int | None                   # rally the tag counts in; None outside rallies


class StatLine(BaseModel):
    team: Team
    number: int | None                      # None: team total
    name: str | None
    set_no: int | None                      # None: whole match
    attempts: int
    kills: int
    attack_errors: int
    efficiency: float | None                # (kills - errors) / decided attempts
    kill_rate: float | None
    serves: int
    aces: int
    serve_errors: int
    unknown: int
    incomplete: bool


class Stats(BaseModel):
    lines: list[StatLine]
    rallies: int
    tagged_rallies: int                     # rallies with at least one tag
    outside: int                            # tags not in any rally (not counted)


def check_unique(players: list[RosterPlayer]) -> None:
    seen = set()
    for pl in players:
        if (pl.team, pl.number) in seen:
            raise HTTPException(400, f"number {pl.number} is listed twice for team {pl.team.upper()}")
        seen.add((pl.team, pl.number))


@app.get("/videos/{vid}/roster", response_model=Roster)
def get_roster(vid: str):
    video_or_404(vid)
    return Roster(players=db.get_roster(vid))


@app.put("/videos/{vid}/roster", response_model=Roster)
def put_roster(vid: str, roster: Roster):
    """Replace both teams' rosters; rejected (unchanged) when a number appears twice in a team."""
    video_or_404(vid)
    check_unique(roster.players)
    db.replace_roster(vid, [pl.model_dump() for pl in roster.players])
    return Roster(players=db.get_roster(vid))


def stat_rallies(vid: str) -> list[vstats.Rally]:
    rows = db.list_rallies(vid)
    eff = effective_winners(rows)
    return [vstats.Rally(r["idx"], r["start_s"], r["end_s"], w, s.set_no)
            for r, w, s in zip(rows, eff, running_score(eff))]


def stat_tags(vid: str) -> list[vstats.Tag]:
    return [vstats.Tag(t["id"], t["time_s"], t["kind"], t["team"], t["number"], t["outcome"])
            for t in db.list_tags(vid)]


def tags_out(vid: str) -> list[TagOut]:
    return [TagOut(id=r.tag.id, time_s=r.tag.time_s, kind=r.tag.kind, team=r.tag.team, number=r.tag.number,
                   outcome=r.tag.outcome, effective_outcome=r.outcome, inferred=r.inferred, rally_idx=r.rally)
            for r in vstats.outcomes(stat_tags(vid), stat_rallies(vid))]


def valid_tag(kind: str, team: str, number: int, outcome: str | None) -> None:
    if number < 0 or number > 99:
        raise HTTPException(400, "player number must be 0-99")
    try:
        vstats.Tag("check", 0.0, kind, team, number, outcome)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/videos/{vid}/tags", response_model=list[TagOut])
def list_tags(vid: str):
    video_or_404(vid)
    return tags_out(vid)


@app.post("/videos/{vid}/tags", response_model=list[TagOut], status_code=201)
def add_tag(vid: str, tag: TagIn):
    """Tag an attack or a serve; a number not on the roster is added to it. Returns all tags."""
    video_or_404(vid)
    valid_tag(tag.kind, tag.team, tag.number, tag.outcome)
    db.ensure_on_roster(vid, tag.team, tag.number)
    db.add_tag(vid, tag.time_s, tag.kind, tag.team, tag.number, tag.outcome)
    return tags_out(vid)


@app.patch("/videos/{vid}/tags/{tag_id}", response_model=list[TagOut])
def patch_tag(vid: str, tag_id: str, patch: TagPatch):
    video_or_404(vid)
    cur = db.get_tag(vid, tag_id)
    if cur is None:
        raise HTTPException(404, "tag not found")
    fields = patch.model_dump(exclude_unset=True)
    new = {**cur, **fields}
    valid_tag(new["kind"], new["team"], new["number"], new["outcome"])
    if fields:
        db.update_tag(vid, tag_id, **fields)
    if "number" in fields or "team" in fields:
        db.ensure_on_roster(vid, new["team"], new["number"])
    return tags_out(vid)


@app.delete("/videos/{vid}/tags/{tag_id}", response_model=list[TagOut])
def delete_tag(vid: str, tag_id: str):
    video_or_404(vid)
    if not db.delete_tag(vid, tag_id):
        raise HTTPException(404, "tag not found")
    return tags_out(vid)


@app.get("/videos/{vid}/stats", response_model=Stats,
         responses={200: {"content": {"text/csv": {}}, "description": "JSON, or CSV with format=csv"}})
def get_stats(vid: str, format: Literal["json", "csv"] = "json"):
    """Statistics from the tags and the current rallies (winner corrections included), computed on request."""
    v = video_or_404(vid)
    rallies = stat_rallies(vid)
    results = vstats.outcomes(stat_tags(vid), rallies)
    lines = vstats.summarise(results, rallies)
    names = {(p["team"], p["number"]): p["name"] for p in db.get_roster(vid) if p["name"]}
    if format == "csv":
        import csv
        import io
        buf = io.StringIO()
        csv.writer(buf).writerows(vstats.csv_rows(lines, names))
        stem = Path(v["name"]).stem
        return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="{stem}-stats.csv"'})
    return Stats(lines=[StatLine(**ln.as_dict(), name=names.get((ln.team, ln.number))) for ln in lines],
                 rallies=len(rallies), tagged_rallies=len({r.rally for r in results if r.rally is not None}),
                 outside=sum(r.rally is None for r in results))
