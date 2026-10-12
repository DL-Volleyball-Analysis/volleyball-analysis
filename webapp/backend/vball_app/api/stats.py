"""Rosters, coach tags and player statistics (vball.stats)."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from vball import stats as vstats
from vball.scoring import running_score

from ..deps import db, effective_winners, video_or_404
from ..schemas import Roster, RosterPlayer, StatLine, Stats, TagIn, TagOut, TagPatch

router = APIRouter()


def check_unique(players: list[RosterPlayer]) -> None:
    seen = set()
    for pl in players:
        if (pl.team, pl.number) in seen:
            raise HTTPException(400, f"number {pl.number} is listed twice for team {pl.team.upper()}")
        seen.add((pl.team, pl.number))


@router.get("/videos/{vid}/roster", response_model=Roster)
def get_roster(vid: str):
    video_or_404(vid)
    return Roster(players=db.get_roster(vid))


@router.put("/videos/{vid}/roster", response_model=Roster)
def put_roster(vid: str, roster: Roster):
    """Replace both teams' rosters; rejected (unchanged) when a number appears twice in a team."""
    video_or_404(vid)
    check_unique(roster.players)
    db.replace_roster(vid, [pl.model_dump() for pl in roster.players])
    return Roster(players=db.get_roster(vid))


def stat_rallies(vid: str) -> list[vstats.Rally]:
    rows = db.list_rallies(vid)
    eff = effective_winners(rows)
    return [
        vstats.Rally(r["idx"], r["start_s"], r["end_s"], w, s.set_no) for r, w, s in zip(rows, eff, running_score(eff))
    ]


def stat_tags(vid: str) -> list[vstats.Tag]:
    return [
        vstats.Tag(t["id"], t["time_s"], t["kind"], t["team"], t["number"], t["outcome"]) for t in db.list_tags(vid)
    ]


def tags_out(vid: str) -> list[TagOut]:
    return [
        TagOut(
            id=r.tag.id,
            time_s=r.tag.time_s,
            kind=r.tag.kind,
            team=r.tag.team,
            number=r.tag.number,
            outcome=r.tag.outcome,
            effective_outcome=r.outcome,
            inferred=r.inferred,
            rally_idx=r.rally,
        )
        for r in vstats.outcomes(stat_tags(vid), stat_rallies(vid))
    ]


def valid_tag(kind: str, team: str, number: int, outcome: str | None) -> None:
    if number < 0 or number > 99:
        raise HTTPException(400, "player number must be 0-99")
    try:
        vstats.Tag("check", 0.0, kind, team, number, outcome)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/videos/{vid}/tags", response_model=list[TagOut])
def list_tags(vid: str):
    video_or_404(vid)
    return tags_out(vid)


@router.post("/videos/{vid}/tags", response_model=list[TagOut], status_code=201)
def add_tag(vid: str, tag: TagIn):
    """Tag an attack or a serve; a number not on the roster is added to it. Returns all tags."""
    video_or_404(vid)
    valid_tag(tag.kind, tag.team, tag.number, tag.outcome)
    db.ensure_on_roster(vid, tag.team, tag.number)
    db.add_tag(vid, tag.time_s, tag.kind, tag.team, tag.number, tag.outcome)
    return tags_out(vid)


@router.patch("/videos/{vid}/tags/{tag_id}", response_model=list[TagOut])
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


@router.delete("/videos/{vid}/tags/{tag_id}", response_model=list[TagOut])
def delete_tag(vid: str, tag_id: str):
    video_or_404(vid)
    if not db.delete_tag(vid, tag_id):
        raise HTTPException(404, "tag not found")
    return tags_out(vid)


@router.get(
    "/videos/{vid}/stats",
    response_model=Stats,
    responses={200: {"content": {"text/csv": {}}, "description": "JSON, or CSV with format=csv"}},
)
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
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{stem}-stats.csv"'},
        )
    return Stats(
        lines=[StatLine(**ln.as_dict(), name=names.get((ln.team, ln.number))) for ln in lines],
        rallies=len(rallies),
        tagged_rallies=len({r.rally for r in results if r.rally is not None}),
        outside=sum(r.rally is None for r in results),
    )
