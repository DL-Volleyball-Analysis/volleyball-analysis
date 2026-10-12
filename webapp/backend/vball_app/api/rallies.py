"""Rallies with running scores and the user's winner corrections."""
from fastapi import APIRouter, HTTPException

from vball.scoring import running_score

from ..deps import db, effective_winners, video_or_404
from ..schemas import Rally, RallyPatch, Score

router = APIRouter()


def rallies_out(vid: str) -> list[Rally]:
    rows = db.list_rallies(vid)
    eff = effective_winners(rows)
    return [Rally(**r, effective_winner=w, score=Score(**s.__dict__))
            for r, w, s in zip(rows, eff, running_score(eff))]


@router.get("/videos/{vid}/rallies", response_model=list[Rally])
def list_rallies(vid: str):
    video_or_404(vid)
    return rallies_out(vid)


@router.patch("/videos/{vid}/rallies/{idx}", response_model=list[Rally])
def correct_rally(vid: str, idx: int, patch: RallyPatch):
    """Set (or clear, with null) the user's winner for one rally; returns all rallies with new scores."""
    video_or_404(vid)
    if not db.set_rally_override(vid, idx, patch.winner):
        raise HTTPException(404, "rally not found")
    return rallies_out(vid)
