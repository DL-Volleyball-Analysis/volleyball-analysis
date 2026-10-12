"""Change follow-camera-motion: the 3D stage takes the camera of each flight's own frame."""

import cv2
import numpy as np

from vball import pipeline
from vball.calibration import look_at
from vball.camera_motion import Motion
from vball.court_keypoints import CORNER_IDS, k6y7r_points_3d

SIZE = (1920, 1080)
EYE = [9.0, -14.0, 7.5]


def cam_at(f: int):
    """A camera that pans (rotates in place) along the court, 1 cm of aim per frame."""
    return look_at(EYE, [6.0 + f / 100, 4.5, 0.5], 1600.0, SIZE)


def motion(n: int) -> Motion:
    grid = np.array([[x, y, z] for x in (0, 9, 18) for y in (0, 9) for z in (0, 3)], float)
    steps = [np.eye(3)]
    for f in range(1, n):
        H, _ = cv2.findHomography(cam_at(f - 1).project(grid), cam_at(f).project(grid))
        steps.append(H)
    return Motion(np.stack(steps))


def test_each_flight_gets_the_camera_of_its_own_frame():
    m = motion(301)
    kp0 = np.column_stack([cam_at(0).project(k6y7r_points_3d()), np.ones(14)])
    court = {
        "shots": [
            {
                "start_frame": 0,
                "end_frame": 300,
                "status": "ok",
                "samples": [{"frame": 0, "corners_px": kp0[CORNER_IDS, :2].tolist(), "keypoints": kp0.tolist()}],
            }
        ]
    }
    cal, why = pipeline.trajectory.flight_camera(court, 300, SIZE, m)
    assert why is None
    true = cam_at(300).project(k6y7r_points_3d())
    assert np.abs(cal.camera.project(k6y7r_points_3d()) - true).max() < 2.0
    still, _ = pipeline.trajectory.flight_camera(court, 300, SIZE, None)  # without motion: the camera of frame 0
    assert np.abs(still.camera.project(k6y7r_points_3d()) - true).max() > 50


def test_ball_positions_move_to_the_reference_frame():
    m = motion(11)
    ball = np.array([9.0, 4.5, 3.0])
    uv = np.array([cam_at(f).project(ball[None])[0] for f in range(11)])
    uv[3] = np.nan
    out = pipeline.trajectory.to_frame(m, uv, 0, range(11), 10)
    want = cam_at(10).project(ball[None])[0]
    assert np.abs(out[[0, 5, 10]] - want).max() < 0.5 and np.isnan(out[3]).all()
    assert np.array_equal(pipeline.trajectory.to_frame(None, uv, 0, range(11), 10), uv, equal_nan=True)
