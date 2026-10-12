"""Change verify-court-by-lines: still shots are decided by the painted lines of their background plate."""
import cv2
import numpy as np
import pytest
from test_api import run_worker_once, upload

from vball.calibration import look_at
from vball.court import LINES
from vball.court_keypoints import CORNER_IDS, k6y7r_points_3d

SIZE = (640, 360)
CAM = look_at([-9.0, 4.5, 8.0], [8.0, 4.5, 0.0], 500.0, SIZE)  # a fixed camera behind an end line
pytestmark = pytest.mark.line_evidence


@pytest.fixture(scope="module")
def end_line_clip(tmp_path_factory):
    """3 s of a painted court seen from behind an end line, with a 'player' running across it."""
    pts = np.array([[0, 0], [18, 0], [18, 9], [0, 9]], float)
    H, _ = cv2.findHomography(pts, CAM.project(np.c_[pts, np.zeros(4)]))
    floor = np.full((SIZE[1], SIZE[0], 3), (70, 120, 180), np.uint8)
    for a, b in LINES.values():
        q = cv2.perspectiveTransform(np.linspace(a, b, 200).reshape(-1, 1, 2), H).reshape(-1, 2)
        cv2.polylines(floor, [q.astype(np.int32)], False, (255, 255, 255), 2, cv2.LINE_AA)
    path = tmp_path_factory.mktemp("clips") / "end_line.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, SIZE)
    for i in range(75):
        f = floor.copy()
        cv2.rectangle(f, (40 + 7 * i, 200), (70 + 7 * i, 280), (30, 30, 160), -1)
        w.write(f)
    w.release()
    return path


def test_lines_replace_a_squeezed_keypoint_court(client, end_line_clip, fake_ball, monkeypatch, tmp_path):
    from vball import pipeline
    weights = tmp_path / "court_kpt.pt"
    weights.write_bytes(b"")
    monkeypatch.setattr(pipeline.config, "COURT_MODELS", {"gym": weights})
    squeezed = k6y7r_points_3d()
    squeezed[:, 0] *= 0.5  # the whole court in the near half, as the keypoint models do on end-line views
    monkeypatch.setattr(pipeline.models, "court_detector",
                        lambda w: (lambda frame: np.column_stack([CAM.project(squeezed), np.full(14, 0.9)])))
    v = upload(client, end_line_clip)
    assert run_worker_once()["status"] == "done"
    import main
    court = pipeline.load_stage(main.RESULTS / v["id"], "court")
    shot = court["shots"][0]
    assert shot["source"] == "lines" and shot["status"] == "ok" and shot["lines"]["good_lines"] >= 5
    true = CAM.project(k6y7r_points_3d()[CORNER_IDS])
    got = np.array(shot["samples"][len(shot["samples"]) // 2]["corners_px"])
    assert min(np.abs(got - true).max(), np.abs(got[[2, 3, 0, 1]] - true).max()) < 4.0
