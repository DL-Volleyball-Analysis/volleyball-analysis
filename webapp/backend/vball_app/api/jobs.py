"""Analysis jobs and stage results."""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from vball import pipeline

from ..db import FINISHED
from ..deps import db, video_or_404
from ..schemas import Job, JobRequest, StageInfo
from ..settings import RESULTS

router = APIRouter()


@router.post("/videos/{vid}/jobs", response_model=Job, status_code=201)
def start_job(vid: str, req: JobRequest):
    video_or_404(vid)
    if db.active_job(vid):
        raise HTTPException(409, "analysis already queued or running")
    return db.add_job(vid, req.from_stage)


@router.get("/videos/{vid}/jobs/latest", response_model=Job | None)
def latest_job(vid: str):
    video_or_404(vid)
    return db.latest_job(vid)


@router.get("/videos/{vid}/jobs/stream")
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

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/videos/{vid}/stages", response_model=list[StageInfo])
def stages(vid: str):
    video_or_404(vid)
    out = []
    for name in pipeline.STAGES:
        res = pipeline.load_stage(RESULTS / vid, name)
        if res is None:
            out.append(StageInfo(name=name, status="pending"))
            continue
        res = dict(res)
        message = res.pop("message", None)
        if name == "court" and (n := len(db.court_corrections(vid))):
            message = f"{message or ''} {n} camera shot{'s' if n > 1 else ''} set by you.".strip()
        out.append(
            StageInfo(
                name=name, status=res.pop("status"), version=res.pop("version", None), message=message, summary=res
            )
        )
    return out
