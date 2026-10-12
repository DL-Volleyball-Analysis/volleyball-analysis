"""Volleyball analysis API.

Run: uvicorn vball_app.main:app --reload   (plus `python -m vball_app.worker` for analysis)
Heavy work never runs in this process: endpoints only queue jobs and read stage results.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import actions, court, jobs, rallies, stats, tracks, videos
from .settings import SETTINGS, configure_logging
from .startup import check_models


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    check_models()
    yield


app = FastAPI(title="Volleyball Analysis API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(SETTINGS.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (videos, jobs, court, tracks, rallies, actions, stats):
    app.include_router(module.router)
