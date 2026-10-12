"""Request and response models of the API (the frontend's types are generated from them: npm run gen:api)."""

from typing import Literal

from pydantic import BaseModel

from vball.pipeline import Stage

Team = Literal["a", "b"]


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


class CourtSample(BaseModel):
    frame: int
    corners_px: list[list[float]]  # far left, far right, near right, near left


class CourtShot(BaseModel):
    shot: int
    start_frame: int
    end_frame: int
    status: Literal["ok", "needs_review", "failed"]
    model: str | None = None
    corrected: bool = False
    samples: list[CourtSample]  # the frontend interpolates corners between samples


class CourtOut(BaseModel):
    status: str  # the court stage status (pending, done, unavailable, ...)
    message: str | None = None
    fps: float | None = None
    shots: list[CourtShot] = []


class CourtCorrection(BaseModel):
    frame: int
    points_px: list[list[float]]  # four image points, in the preset's order
    preset: Literal["corners", "near_half"] = "corners"  # vball.court_registration.CORRECTION_PRESETS


class CourtCorrected(BaseModel):
    court: CourtOut
    queued: bool  # a re-analysis from the players stage was queued


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
    x: list[float | None]  # image pixels, None when the ball is not detected
    y: list[float | None]


class BallCoverage(BaseModel):
    duration_s: float
    coverage: list[float]  # fraction of frames with a detection, per equal time bin


class PlayerBox(BaseModel):
    frame: int
    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    interpolated: bool
    court_x: float | None  # metres; None without a court mapping
    court_y: float | None
    side: Literal["a", "b"] | None
    team: Literal["a", "b"] | None = None  # by shirt colour; None when not trusted
    role: Literal["player", "other"] = "player"  # other: officials, staff, spectators (shown, not counted)


class PlayerWindow(BaseModel):
    fps: float
    placed: bool  # positions and the on-court filter were applied
    boxes: list[PlayerBox]


class FlightSample(BaseModel):
    t: float  # seconds in the video
    x: float  # court metres (vball.court frame, z up)
    y: float
    z: float
    observed: bool  # the ball was detected in this frame (else the position comes from the fit)


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
    dropped: int = 0  # detections left out as inconsistent with the flight


class ImportRequest(BaseModel):
    path: str


class JobRequest(BaseModel):
    from_stage: Stage = "decode"


class RallyPatch(BaseModel):
    winner: Team | None


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
    outcome: Outcome | None  # set by the user
    effective_outcome: Literal["kill", "ace", "error", "in_play", "unknown", "outside"]
    inferred: bool  # effective outcome comes from the rally winner / position
    rally_idx: int | None  # rally the tag counts in; None outside rallies


class StatLine(BaseModel):
    team: Team
    number: int | None  # None: team total
    name: str | None
    set_no: int | None  # None: whole match
    attempts: int
    kills: int
    attack_errors: int
    efficiency: float | None  # (kills - errors) / decided attempts
    kill_rate: float | None
    serves: int
    aces: int
    serve_errors: int
    unknown: int
    incomplete: bool


class Stats(BaseModel):
    lines: list[StatLine]
    rallies: int
    tagged_rallies: int  # rallies with at least one tag
    outside: int  # tags not in any rally (not counted)


class ActionEvent(BaseModel):
    action: Literal["block", "receive", "serve", "set", "spike"]
    track_id: int | None
    start_s: float
    end_s: float
    peak_conf: float
    number: int | None  # the track's shirt number when the vote is clear
    team: Team | None  # by shirt colour, else the side of the net


class ShirtNumber(BaseModel):
    track_id: int
    number: int | None  # None: no clear vote (shown by tracking id)
    share: float
    readings: int


class Suggestion(BaseModel):
    """A tag proposed from an action event; never counted until the coach posts it as a tag."""

    id: str
    kind: TagKind
    time_s: float
    team: Team | None
    number: int | None  # None: the coach has to give it
    track_id: int | None
    status: Literal["open", "accepted", "dismissed"]


class NumberSegment(BaseModel):
    """A stretch of a track with one shirt number (time-local vote); outside segments: the tracking id."""

    track_id: int
    start_s: float
    end_s: float
    number: int


class ActionsOut(BaseModel):
    events: list[ActionEvent]
    numbers: list[ShirtNumber]
    segments: list[NumberSegment] = []
    suggestions: list[Suggestion]
