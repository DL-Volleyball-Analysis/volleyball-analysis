"""Court per camera shot and the user's court corrections."""

from fastapi import APIRouter, HTTPException

from vball import court_registration, pipeline

from ..deps import db, video_or_404
from ..schemas import CourtCorrected, CourtCorrection, CourtOut, CourtSample, CourtShot
from ..settings import RESULTS

router = APIRouter()


def court_out(vid: str) -> CourtOut:
    """The court stage result with the user's corrections overlaid."""
    res = pipeline.load_stage(RESULTS / vid, "court")
    if res is None:
        return CourtOut(status="pending")
    dec = pipeline.load_stage(RESULTS / vid, "decode")
    court = pipeline.corrected_court(res, dec, db.court_corrections(vid), RESULTS / vid)
    assert court is not None  # corrections are overlaid on an existing result
    shots = [
        CourtShot(
            shot=k,
            start_frame=s["start_frame"],
            end_frame=s["end_frame"],
            status=s["status"],
            model=s.get("model"),
            corrected=bool(s.get("corrected")),
            samples=[CourtSample(frame=x["frame"], corners_px=x["corners_px"]) for x in s.get("samples", [])],
        )
        for k, s in enumerate(court.get("shots", []))
    ]
    return CourtOut(
        status=court.get("status", "done"), message=court.get("message"), fps=(dec or {}).get("fps"), shots=shots
    )


def requeue_from_players(vid: str) -> bool:
    """Players, trajectory and later stages use the court: rerun them (court and ball results are reused).
    With a job already queued or running nothing is added; the next analysis applies the correction."""
    if db.active_job(vid):
        return False
    db.add_job(vid, "players")
    return True


@router.get("/videos/{vid}/court", response_model=CourtOut)
def get_court(vid: str):
    video_or_404(vid)
    return court_out(vid)


@router.put("/videos/{vid}/court/{shot}", response_model=CourtCorrected)
def correct_court(vid: str, shot: int, req: CourtCorrection):
    video_or_404(vid)
    res = pipeline.load_stage(RESULTS / vid, "court")
    dec = pipeline.load_stage(RESULTS / vid, "decode")
    shots = (res or {}).get("shots", [])
    if not 0 <= shot < len(shots):
        raise HTTPException(404, "shot not found")
    assert dec is not None  # the court stage runs after decode
    if not shots[shot]["start_frame"] <= req.frame <= shots[shot]["end_frame"]:
        raise HTTPException(422, "the frame is outside this shot")
    ids = court_registration.CORRECTION_PRESETS[req.preset]
    try:
        court_registration.corrected_sample(req.frame, req.points_px, (dec["width"], dec["height"]), ids)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    db.set_court_correction(vid, shot, req.frame, req.points_px, list(ids))
    return CourtCorrected(court=court_out(vid), queued=requeue_from_players(vid))


@router.delete("/videos/{vid}/court/{shot}", response_model=CourtCorrected)
def clear_court(vid: str, shot: int):
    video_or_404(vid)
    if not db.clear_court_correction(vid, shot):
        raise HTTPException(404, "no correction for this shot")
    return CourtCorrected(court=court_out(vid), queued=requeue_from_players(vid))
