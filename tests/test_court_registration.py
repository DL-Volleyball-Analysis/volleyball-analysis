import numpy as np
import pytest

from vball.calibration import look_at
from vball.court_keypoints import (CORNER_IDS, K6Y7R_FLIP_IDX, corners_from_homography, court_is_plausible,
                                   fit_homography, k6y7r_points_3d)
from vball.court_registration import (CONFIG, calibration_samples, corners_at, mapping_at, register_shot,
                                      sample_frames, shot_status, smooth_corners)

SIZE = (1920, 1080)
CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1600.0, SIZE)
TRUE_CORNERS = CAM.project(k6y7r_points_3d()[CORNER_IDS])


def keypoints(camera=CAM, noise=0.0, seed=0, conf=0.9):
    """14 x (x, y, conf) as a pose model would return for this camera."""
    xy = camera.project(k6y7r_points_3d()) + np.random.default_rng(seed).normal(0, noise, (14, 2))
    return np.column_stack([xy, np.full(14, conf)])


# --- fit_homography and the sanity check (tasks 1.1, 1.2) ---

@pytest.mark.parametrize("seed", range(3))
def test_fit_recovers_the_corners_with_noise_and_an_outlier(seed):
    kp = keypoints(noise=0.5, seed=seed)
    kp[3, :2] += [80, -60]  # one keypoint far off: RANSAC drops it
    H, err = fit_homography(kp, SIZE)
    assert np.abs(corners_from_homography(H) - TRUE_CORNERS).max() < 1.0
    assert err < 0.001


def test_low_confidence_points_are_ignored_and_four_are_needed():
    kp = keypoints()
    kp[1:8, 2] = 0.1  # confident: 0 (far left corner), 8, 9
    assert fit_homography(kp, SIZE) is None
    kp[4, 2] = 0.9  # 0, 4, 8, 9: two per sideline, no three collinear
    assert fit_homography(kp, SIZE) is not None
    kp[[0, 1, 2, 3, 4], 2] = 0.1  # only the near sideline (6-9): collinear, no homography
    kp[6, 2] = 0.9
    assert fit_homography(kp, SIZE) is None


def test_mirrored_court_is_rejected():
    kp = keypoints()
    mirrored = kp[K6Y7R_FLIP_IDX]  # numbering mirrored without mirroring the image
    assert fit_homography(mirrored, SIZE) is None
    assert court_is_plausible(TRUE_CORNERS, SIZE)
    assert not court_is_plausible(TRUE_CORNERS[[1, 0, 3, 2]], SIZE)


def test_folded_and_tiny_courts_are_rejected():
    folded = TRUE_CORNERS[[0, 2, 1, 3]]  # self-intersecting
    assert not court_is_plausible(folded, SIZE)
    centre = TRUE_CORNERS.mean(axis=0)
    tiny = centre + 0.05 * (TRUE_CORNERS - centre)
    assert not court_is_plausible(tiny, SIZE)


# --- per-shot registration (tasks 2.1-2.4) ---

def test_samples_stay_inside_the_shot():
    frames = sample_frames(100, 160, fps=30)
    assert frames[0] == 100 and frames[-1] == 160 and all(100 <= f <= 160 for f in frames)
    assert frames[:3] == [100, 106, 112]


def test_smoothing_removes_one_outlier_and_keeps_a_pan():
    pan = [TRUE_CORNERS + [5.0 * i, 0] for i in range(15)]
    jumpy = list(pan)
    jumpy[4] = pan[4] + [200, 150]
    out = smooth_corners(jumpy)
    assert np.abs(out[4] - pan[4]).max() <= 5  # the jump is gone (within one pan step)
    for i in (0, 1, 10, 13, 14):  # away from the jump, ends of the shot included: the pan is unchanged
        assert np.abs(out[i] - pan[i]).max() < 1e-9


def test_mapping_follows_a_panning_camera_between_samples():
    # camera pans along the court over 60 frames at 30 fps
    def cam_at(f):
        return look_at([9.0 + f / 20, -14.0, 7.5], [9.0 + f / 20, 4.5, 0.5], 1600.0, SIZE)
    shot = register_shot(0, 60, 30.0, SIZE, lambda f: keypoints(cam_at(f)))
    assert shot["status"] == "ok" and [s["frame"] for s in shot["samples"]][:3] == [0, 6, 12]
    court = {"shots": [shot]}
    s6 = shot["samples"][1]
    assert np.allclose(corners_at(court, 6), s6["corners_px"])
    mid = corners_at(court, 9)
    assert np.allclose(mid, (np.array(s6["corners_px"]) + np.array(shot["samples"][2]["corners_px"])) / 2)
    # the mapping at frame 9 lands the corners near where the camera at frame 9 sees them
    true9 = cam_at(9).project(k6y7r_points_3d()[CORNER_IDS])
    assert np.abs(corners_from_homography(mapping_at(court, 9, SIZE)) - true9).max() < 2.0


def test_hidden_court_fails_without_a_mapping():
    shot = register_shot(0, 30, 30.0, SIZE, lambda f: np.zeros((14, 3)))
    assert shot["status"] == "failed" and shot["error"] is None and shot["samples"] == []
    assert mapping_at({"shots": [shot]}, 10) is None
    assert mapping_at({"shots": [shot]}, 999) is None  # outside any shot


def test_status_rules():
    assert shot_status(10, 1, [0.001]) == ("failed", None)
    assert shot_status(10, 8, [0.002, 0.003])[0] == "ok"
    assert shot_status(10, 3, [0.002, 0.003])[0] == "needs_review"  # under half the samples valid
    assert shot_status(10, 8, [CONFIG["review_error"] * 2] * 8)[0] == "needs_review"  # large error


def test_noisy_keypoints_need_review():
    for noise in (60.0, 100.0):  # 100 px once fooled an inlier-RMS error into ~0 (four exact inliers)
        shot = register_shot(0, 30, 30.0, SIZE, lambda f: keypoints(noise=noise, seed=f))
        assert shot["status"] in ("needs_review", "failed")
    clean = register_shot(0, 30, 30.0, SIZE, lambda f: keypoints(noise=1.0, seed=f))
    assert clean["status"] == "ok"


def test_calibration_samples_come_from_the_shot_nearest_the_middle_first():
    shot = register_shot(0, 60, 30.0, SIZE, lambda f: keypoints())
    samples = calibration_samples({"shots": [shot]}, 20, 30)
    assert samples[0]["frame"] == 24 and len(samples[0]["keypoints"]) == 14


def inconsistent_keypoints():
    """Floor points from the true camera; net points at the two posts pushed 60 px apart, which no single
    pinhole camera produces. (A clean squeeze of the floor into the near half is NOT caught: another camera
    explains it. Model v2's real failures were caught because its floor points were also internally
    inconsistent; see docs/results/court-keypoints.md.)"""
    kp = keypoints()
    kp[[10, 11], 0] += 60
    kp[[12, 13], 0] -= 60
    return kp


def test_keypoints_no_single_camera_explains_need_review():
    kp = inconsistent_keypoints()
    assert fit_homography(kp, SIZE)[1] < 0.001  # the floor homography alone looks perfect
    shot = register_shot(0, 30, 30.0, SIZE, lambda f: kp)
    assert shot["status"] == "needs_review" and shot["consistency"] > CONFIG["review_consistency"]
    good = register_shot(0, 30, 30.0, SIZE, lambda f: keypoints(noise=1.0, seed=f))
    assert good["status"] == "ok" and good["consistency"] < CONFIG["review_consistency"]


def test_without_net_points_the_consistency_check_is_skipped():
    kp = keypoints()
    kp[10:, 2] = 0.0
    shot = register_shot(0, 30, 30.0, SIZE, lambda f: kp)
    assert shot["consistency"] is None and shot["status"] == "ok"


def test_later_stages_only_use_shots_that_are_ok():
    shot = register_shot(0, 30, 30.0, SIZE, lambda f: inconsistent_keypoints())
    court = {"shots": [shot]}
    assert shot["status"] == "needs_review"
    assert mapping_at(court, 10, SIZE) is None and calibration_samples(court, 0, 30) == []
    assert mapping_at(court, 10, SIZE, statuses=("ok", "needs_review")) is not None  # still there for review
