import numpy as np
import pytest

from vball.calibration import calibrate, look_at
from vball.court_keypoints import K6Y7R_NET_IDS, NET_TOP_MEN, NET_TOP_WOMEN, k6y7r_points_3d

SIZE = (1920, 1080)
# broadcast-like: behind the near sideline, high, looking at the court centre
TRUE = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1600.0, SIZE)


def keypoints(camera, net_top=NET_TOP_MEN, noise=0.0, seed=0):
    pts = camera.project(k6y7r_points_3d(net_top))
    return pts + np.random.default_rng(seed).normal(0, noise, pts.shape)


def test_camera_projects_far_sideline_left_to_right():
    # image-based numbering: 0-4 on the far sideline (higher in the image), left to right
    pts = keypoints(TRUE)
    assert np.all(np.diff(pts[:5, 0]) > 0)
    assert pts[:5, 1].max() < pts[5:10, 1].min()


@pytest.mark.parametrize("seed", range(5))
def test_recovers_known_camera_from_noisy_keypoints(seed):
    cal = calibrate(keypoints(TRUE, noise=1.0, seed=seed), SIZE)
    assert cal.status == "ok"
    assert abs(cal.camera.focal / TRUE.focal - 1) < 0.02
    assert np.linalg.norm(cal.camera.position - TRUE.position) < 0.2
    assert cal.reprojection_px < 2.0


@pytest.mark.parametrize("height", [NET_TOP_MEN, NET_TOP_WOMEN])
def test_picks_the_net_height_that_fits(height):
    cal = calibrate(keypoints(TRUE, net_top=height, noise=0.3), SIZE)
    assert cal.net_top == height


def test_floor_only_when_no_net_point_is_visible():
    pts = keypoints(TRUE, noise=0.5)
    pts[K6Y7R_NET_IDS] = np.nan
    cal = calibrate(pts, SIZE)
    assert cal.status == "floor_only" and cal.net_top is None
    assert abs(cal.camera.focal / TRUE.focal - 1) < 0.05


def test_too_few_floor_points_is_unusable():
    pts = keypoints(TRUE)
    pts[[0, 1, 2, 3, 4, 5, 6]] = np.nan  # three floor points left
    cal = calibrate(pts, SIZE)
    assert cal.status == "unusable" and "floor keypoints" in cal.reason


def test_a_few_wrong_keypoints_do_not_spoil_the_camera():
    pts = keypoints(TRUE, noise=0.5)
    pts[[1, 8]] += [[60, -40], [-70, -20]]  # two attack-line points far off (robust loss)
    cal = calibrate(pts, SIZE)
    assert cal.status == "ok"
    assert np.linalg.norm(cal.camera.position - TRUE.position) < 0.3


def test_inconsistent_keypoints_fail_the_quality_gate():
    cal = calibrate(keypoints(TRUE, noise=40.0), SIZE)  # every point tens of pixels off
    assert cal.status == "unusable" and "reprojection error" in cal.reason


def test_ray_passes_through_the_projected_point():
    p = np.array([4.0, 2.0, 3.0])
    uv = TRUE.project(p[None])[0]
    d = TRUE.ray(uv)
    to_p = p - TRUE.position
    assert np.linalg.norm(np.cross(d, to_p / np.linalg.norm(to_p))) < 1e-9
