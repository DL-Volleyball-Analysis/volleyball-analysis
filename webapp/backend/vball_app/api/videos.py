"""Video library: upload, import, list, delete, the video file."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from vball import pipeline
from vball.scoring import running_score

from ..deps import db, effective_winners, video_or_404
from ..schemas import ImportRequest, ScoreSummary, Video
from ..settings import RESULTS, UPLOADS, VIDEO_SUFFIXES

router = APIRouter()


def score_summary(vid: str) -> ScoreSummary | None:
    rows = db.list_rallies(vid)
    if not rows:
        return None
    last = running_score(effective_winners(rows))[-1]
    return ScoreSummary(
        set_no=last.set_no,
        a=last.a,
        b=last.b,
        sets_a=last.sets_a,
        sets_b=last.sets_b,
        rallies=len(rows),
        corrected=sum(r["winner_override"] is not None for r in rows),
        demo=any(r["source"] == "demo" for r in rows),
    )


def video_out(v: dict) -> Video:
    return Video(**v, job=db.latest_job(v["id"]), score=score_summary(v["id"]))


def register(name: str, path: Path) -> Video:
    try:
        meta = pipeline.decode.video_meta(path)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    v = db.add_video(name, str(path), meta)
    db.add_job(v["id"], "decode")  # analysis starts right after upload
    return video_out(v)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/videos", response_model=list[Video])
def list_videos():
    return [video_out(v) for v in db.list_videos()]


@router.post("/videos", response_model=Video, status_code=201)
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


@router.post("/videos/import", response_model=Video, status_code=201)
def import_video(req: ImportRequest):
    """Register a video already on this machine without copying it (local use)."""
    path = Path(req.path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
        raise HTTPException(400, "not a video file on this machine")
    return register(path.stem, path)


@router.get("/videos/{vid}", response_model=Video)
def get_video(vid: str):
    return video_out(video_or_404(vid))


@router.delete("/videos/{vid}", status_code=204)
def delete_video(vid: str):
    v = video_or_404(vid)
    db.delete_video(vid)
    path = Path(v["path"])
    if path.parent.resolve() == UPLOADS.resolve():  # never delete imported originals
        path.unlink(missing_ok=True)
    shutil.rmtree(RESULTS / vid, ignore_errors=True)


@router.get("/videos/{vid}/file")
def video_file(vid: str):
    """The video itself; FileResponse handles Range requests, so seeking works."""
    path = Path(video_or_404(vid)["path"])
    if not path.exists():
        raise HTTPException(404, "video file missing on disk")
    return FileResponse(path)
