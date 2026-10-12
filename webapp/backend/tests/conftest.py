import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session", autouse=True)
def data_dir(tmp_path_factory):
    # settings reads this at import, so set it before any backend module is imported
    d = tmp_path_factory.mktemp("webapp_data")
    os.environ["VBALL_WEBAPP_DATA"] = str(d)
    return d


@pytest.fixture(autouse=True)
def empty_db(data_dir):
    import main
    with main.db.connect() as c:
        tables = ("court_corrections", "dismissed_suggestions", "tags", "rosters", "rallies", "jobs", "videos")
        c.executescript("".join(f"DELETE FROM {t};" for t in tables))


@pytest.fixture(scope="session")
def clip(tmp_path_factory) -> Path:
    """2 s at 25 fps: one second of green 'court', then a cut to a red shot."""
    path = tmp_path_factory.mktemp("clips") / "match.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (320, 180))
    for i in range(50):
        frame = np.full((180, 320, 3), (40, 160, 40) if i < 25 else (40, 40, 200), np.uint8)
        cv2.circle(frame, (10 + 6 * (i % 25), 90), 5, (255, 255, 255), -1)
        w.write(frame)
    w.release()
    return path


@pytest.fixture
def fake_ball(monkeypatch):
    """Replace VballNet inference: ball seen on even frames only."""
    from vball import pipeline

    def track(video, model, out_dir=None, force=False):
        n = pipeline.decode.video_meta(Path(video))["frames"]
        f = np.arange(n)
        vis = (f % 2 == 0).astype(int)
        return pd.DataFrame({"frame": f, "visible": vis, "x": np.where(vis, 10.0 + f, np.nan),
                             "y": np.where(vis, 90.0, np.nan), "radius": 5})

    monkeypatch.setattr("vball.ball.track", track)


@pytest.fixture
def client():
    import main
    from fastapi.testclient import TestClient
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def fake_players(monkeypatch):
    """Replace YOLO + BoT-SORT: two tracks in every frame, one standing on court and one far outside it
    (bottom-centres at image (150, 100) and (300, 20)). Consumes the frame generator like the real one."""

    def track_frames(frames, src_fps, cfg=None, step=None):
        rows = []
        for i, _ in enumerate(frames):
            rows.append((i, 1, 130.0, 60.0, 170.0, 100.0, 0.9, False))
            rows.append((i, 2, 280.0, 0.0, 320.0, 20.0, 0.8, False))
        return pd.DataFrame(rows, columns=["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"])

    monkeypatch.setattr("vball.players.track_frames", track_frames)


@pytest.fixture(autouse=True)
def no_action_models(monkeypatch, tmp_path):
    """The real action and digit weights may be in models/; tests run without them unless they install fakes."""
    from vball import pipeline
    monkeypatch.setattr(pipeline.config, "ACTION_MODEL", tmp_path / "missing_action.pt")
    monkeypatch.setattr(pipeline.config, "JERSEY_MODEL", tmp_path / "missing_digits.pt")
    monkeypatch.setattr(pipeline.config, "PERSON_MODEL", tmp_path / "missing_person.pt")
    monkeypatch.setattr(pipeline.config, "GENERAL_PLAYER_MODEL", tmp_path / "missing_general.pt")
    monkeypatch.setattr(pipeline.config, "RALLY_MODEL", tmp_path / "missing_rally.joblib")


@pytest.fixture(autouse=True)
def no_line_evidence(monkeypatch, request):
    """The test clips are flat colour with no painted lines, so line evidence (still shots, change
    verify-court-by-lines) would mark every fake court as doubtful. Off by default; tests marked `line_evidence`
    keep it."""
    if "line_evidence" in request.keywords:
        return
    monkeypatch.setattr("vball.court_registration.still", lambda *a, **k: False)


def pytest_configure(config):
    config.addinivalue_line("markers", "line_evidence: keep the still-shot line evidence in the court stage")
