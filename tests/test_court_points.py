import numpy as np

from vball.calibration import look_at
from vball.evaluation.court_points import POINTS, errors, summary, to_court


def homography(cam):
    """Court floor (z = 0) -> image homography of a camera."""
    floor = np.array([[0, 0, 0], [18, 0, 0], [18, 9, 0], [0, 9, 0]], float)
    import cv2

    H, _ = cv2.findHomography(floor[:, :2], cam.project(floor))
    return H


CAM = look_at([-6.0, 4.5, 4.0], [9.0, 4.5, 0.0], 1500.0, (1920, 1080))  # behind the near end line


def test_exact_clicks_give_zero_error_and_skips_are_left_out():
    H = homography(CAM)
    labels = {n: CAM.project(np.array([[x, y, 0.0]]))[0].tolist() for n, (x, y) in POINTS.items()}
    labels["near attack line, left end"] = None
    e = errors(H, labels)
    assert len(e) == 5 and max(e.values()) < 1e-4  # a tenth of a millimetre
    assert summary(e)["median_m"] == 0.0 and summary({}) == {"points": 0}


def test_error_is_taken_under_the_court_symmetry():
    H = homography(CAM)
    # the fit may call the far end x = 0: clicks of the near corners map to x = 18 and still count as right
    flipped = np.array([[[18 - x, 9 - y, 0.0]] for x, y in POINTS.values()])[:, 0]
    labels = dict(zip(POINTS, CAM.project(flipped).tolist()))
    assert max(errors(H, labels).values()) < 1e-4  # a tenth of a millimetre
    shifted = {n: [u + 15, v] for n, (u, v) in labels.items()}  # 15 px off: a measurable error
    assert 0.01 < summary(errors(H, shifted))["median_m"] < 1.0
    assert np.allclose(to_court(H, CAM.project(np.array([[3.0, 4.0, 0.0]]))), [[3.0, 4.0]])
