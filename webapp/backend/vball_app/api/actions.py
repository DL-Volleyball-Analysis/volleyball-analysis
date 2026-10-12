"""Action events, shirt numbers and the tags they suggest (change add-player-actions)."""

import json

from fastapi import APIRouter, HTTPException

from vball import jersey

from ..deps import db, players_table, video_or_404
from ..schemas import ActionEvent, ActionsOut, NumberSegment, ShirtNumber, Suggestion
from ..settings import RESULTS

router = APIRouter()

SUGGEST = {"spike": "attack", "serve": "serve"}
ACCEPT_WINDOW_S = 1.0  # a tag of the same kind this close to a suggestion accepts it
RALLY_MARGIN_S = 1.0  # actions this close to a detected rally still count (a serve toss starts before it)


@router.get("/videos/{vid}/actions", response_model=ActionsOut)
def actions(vid: str):
    """Action events, shirt numbers per track and the tags they suggest (change add-player-actions)."""
    v = video_or_404(vid)
    path = RESULTS / vid / "action_events.json"
    if not path.exists():
        raise HTTPException(404, "action recognition not run yet")
    data = json.loads(path.read_text())
    numbers = {int(t): n for t, n in data.get("numbers", {}).items()}
    fps = v["fps"] or 30.0
    reach = int(data.get("reach", 0))
    segs = {int(t): [tuple(x) for x in sg] for t, sg in data.get("segments", {}).items()}

    def number_at(tid, frame):
        """The time-local number when segments exist (stage version 2), else the track's overall vote."""
        if tid is None:
            return None
        if tid in segs:
            return jersey.number_at(segs[tid], frame, reach)
        return (numbers.get(tid) or {}).get("number")

    team_of: dict[int, str] = {}
    csv = RESULTS / vid / "players.csv.gz"
    if csv.exists():
        df = players_table(str(csv), csv.stat().st_mtime)
        for col in ("side", "team"):  # team (shirt colour) overrides side (net) when known
            if col in df:
                for tid, vals in df.groupby("track_id")[col]:
                    vals = vals[vals.astype(str).isin(["a", "b"])]
                    if len(vals):
                        team_of[int(tid)] = str(vals.mode().iloc[0])
    events = [
        ActionEvent(
            action=e["action"],
            track_id=e["track_id"],
            start_s=e["start_s"],
            end_s=e["end_s"],
            peak_conf=e["peak_conf"],
            number=number_at(e["track_id"], e["start_frame"]),
            team=team_of.get(e["track_id"]) if e["track_id"] is not None else None,
        )
        for e in data.get("events", [])
    ]
    detected = [(r["start_s"], r["end_s"]) for r in db.list_rallies(vid) if r["source"] == "model"]
    if detected:  # with detected rallies, actions outside play (warm-up, time-outs, replays) are left out
        keep = [any(a - RALLY_MARGIN_S <= e.start_s <= b + RALLY_MARGIN_S for a, b in detected) for e in events]
        events = [e for e, k in zip(events, keep) if k]
        data["events"] = [raw for raw, k in zip(data.get("events", []), keep) if k]
    tags, dismissed = db.list_tags(vid), db.dismissed_suggestions(vid)
    suggestions = []
    for e, raw in zip(events, data.get("events", [])):
        kind = SUGGEST.get(e.action)
        if kind is None:
            continue
        sid = f"{kind}-{raw['start_frame']}-{e.track_id if e.track_id is not None else 'x'}"
        accepted = any(t["kind"] == kind and abs(t["time_s"] - e.start_s) <= ACCEPT_WINDOW_S for t in tags)
        status = "accepted" if accepted else "dismissed" if sid in dismissed else "open"
        suggestions.append(
            Suggestion(
                id=sid,
                kind=kind,
                time_s=round(e.start_s, 3),
                team=e.team,
                number=e.number,
                track_id=e.track_id,
                status=status,
            )
        )
    segments = [
        NumberSegment(
            track_id=t, start_s=round(max(0, a - reach) / fps, 3), end_s=round((b + reach) / fps, 3), number=n
        )
        for t, sg in sorted(segs.items())
        for a, b, n in sg
        if n is not None
    ]
    return ActionsOut(
        events=events,
        suggestions=suggestions,
        segments=segments,
        numbers=[ShirtNumber(track_id=t, **n) for t, n in sorted(numbers.items())],
    )


@router.post("/videos/{vid}/actions/suggestions/{sid}/dismiss", status_code=204)
def dismiss_suggestion(vid: str, sid: str):
    video_or_404(vid)
    db.dismiss_suggestion(vid, sid)
