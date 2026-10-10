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
        c.executescript("DELETE FROM tags; DELETE FROM rosters; DELETE FROM rallies; DELETE FROM jobs; DELETE FROM videos;")


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
    import pipeline

    def track(video, model, out_dir=None, force=False):
        n = pipeline.video_meta(Path(video))["frames"]
        f = np.arange(n)
        vis = (f % 2 == 0).astype(int)
        return pd.DataFrame({"frame": f, "visible": vis, "x": np.where(vis, 10.0 + f, np.nan),
                             "y": np.where(vis, 90.0, np.nan), "radius": 5})

    monkeypatch.setattr(pipeline.ball, "track", track)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def fake_players(monkeypatch):
    """Replace YOLO + BoT-SORT: two tracks in every frame, one standing on court and one far outside it
    (bottom-centres at image (150, 100) and (300, 20)). Consumes the frame generator like the real one."""
    import pipeline

    def track_frames(frames, src_fps, cfg=None, step=None):
        rows = []
        for i, _ in enumerate(frames):
            rows.append((i, 1, 130.0, 60.0, 170.0, 100.0, 0.9, False))
            rows.append((i, 2, 280.0, 0.0, 320.0, 20.0, 0.8, False))
        return pd.DataFrame(rows, columns=["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"])

    monkeypatch.setattr(pipeline.players, "track_frames", track_frames)


@pytest.fixture(autouse=True)
def no_action_models(monkeypatch, tmp_path):
    """The real action and digit weights may be in models/; tests run without them unless they install fakes."""
    import pipeline
    monkeypatch.setattr(pipeline, "ACTION_MODEL", tmp_path / "missing_action.pt")
    monkeypatch.setattr(pipeline, "JERSEY_MODEL", tmp_path / "missing_digits.pt")
