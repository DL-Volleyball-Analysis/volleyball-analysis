import numpy as np
import pytest

from vball.calibration import look_at
from vball.court_keypoints import (
    CORNER_IDS,
    K6Y7R_FLIP_IDX,
    corners_from_homography,
    court_is_plausible,
    fit_homography,
    k6y7r_points_3d,
)
from vball.court_registration import (
    CONFIG,
    calibration_samples,
    corners_at,
    mapping_at,
    register_shot,
    sample_frames,
    shot_status,
    smooth_corners,
)

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
        shot = register_shot(0, 30, 30.0, SIZE, lambda f, noise=noise: keypoints(noise=noise, seed=f))
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


def test_pick_prefers_status_then_consistency_then_error():
    from vball.court_registration import pick
    def shot(status, consistency=None, error=None):
        return {"start_frame": 0, "end_frame": 9, "status": status, "consistency": consistency, "error": error, "samples": []}
    shots = pick({
        "gym": [shot("ok", 0.010, 0.002), shot("needs_review", 0.05, 0.001), shot("failed"), shot("ok", 0.004, 0.003)],
        "broadcast": [shot("needs_review", 0.001, 0.001), shot("ok", 0.012, 0.004), shot("failed"), shot("ok", 0.004, 0.001)],
    })
    assert [s["model"] for s in shots] == ["gym", "broadcast", "gym", "broadcast"]
    assert shots[0]["status"] == "ok" and shots[1]["status"] == "ok"


def test_pick_with_one_model_keeps_its_shots():
    from vball.court_registration import pick
    one = [{"start_frame": 0, "end_frame": 9, "status": "failed", "consistency": None, "error": None, "samples": []}]
    assert pick({"v2": one}) == [{**one[0], "model": "v2"}] and pick({}) == []


def test_a_correction_overrides_its_shot_and_leaves_the_stored_court_alone():
    from vball.court_registration import apply_corrections, mapping_at
    corners = [[600, 300], [1320, 300], [1700, 800], [220, 800]]
    court = {"status": "done", "shots": [
        {"start_frame": 0, "end_frame": 99, "status": "needs_review", "error": 0.02, "samples": []},
        {"start_frame": 100, "end_frame": 199, "status": "ok", "error": 0.001, "samples": []}]}
    out = apply_corrections(court, [{"shot": 0, "frame": 40, "points_px": corners}], (1920, 1080))
    s = out["shots"][0]
    assert s["status"] == "ok" and s["corrected"] and court["shots"][0]["status"] == "needs_review"
    kp = np.array(s["samples"][0]["keypoints"])
    assert np.allclose(kp[[0, 4, 5, 9], :2], corners) and (kp[:10, 2] == 1).all()
    assert kp[10:, 2].min() == 1 and (kp[10:12, 1] < kp[0, 1]).all()  # far net points above the far sideline
    H = mapping_at(out, 70, (1920, 1080))
    assert H is not None and out["shots"][1] == court["shots"][1]
    assert apply_corrections(court, [], (1920, 1080)) is court


def test_an_implausible_correction_is_rejected():
    import pytest

    from vball.court_registration import corrected_sample
    with pytest.raises(ValueError):
        corrected_sample(0, [[600, 300], [220, 800], [1700, 800], [1320, 300]], (1920, 1080))  # crossed


def test_a_near_half_correction_for_a_camera_behind_the_end_line():
    from vball.court_registration import CORRECTION_PRESETS, corrected_sample
    # centre line left / right (at the net posts' feet), near end line right / left, on a Tokyo 2020 end-line view
    pts = [[355, 680], [1606, 680], [1776, 1060], [190, 1060]]
    s = corrected_sample(100, pts, (1920, 1080), CORRECTION_PRESETS["near_half"])
    c = np.array(s["corners_px"])
    assert c[:, 1].min() < 680  # the far end line lies beyond the centre line, higher in the image
    assert np.allclose(np.array(s["keypoints"])[[2, 7, 9, 0], :2], pts)


# --- camera motion (change follow-camera-motion) ---

def shifting(n: int, dx: float = -3.0):
    """Camera motion where the image moves dx px per frame (a pan), as vball.camera_motion.Motion."""
    from vball.camera_motion import Motion
    step = np.array([[1, 0, dx], [0, 1, 0], [0, 0, 1.0]])
    return Motion(np.stack([np.eye(3)] + [step] * (n - 1)))


def panned(f, dx=-3.0):
    kp = keypoints()
    kp[:, 0] += dx * f
    return kp


def test_motion_compensated_smoothing_keeps_a_fast_pan_and_removes_a_jump():
    frames = list(range(0, 90, 6))
    pan = [TRUE_CORNERS + [-3.0 * f, 0] for f in frames]
    jumpy = list(pan)
    jumpy[2] = pan[2] + [150, 0]
    out = smooth_corners(jumpy, frames=frames, motion=shifting(90))
    assert all(np.abs(o - p).max() < 1e-6 for o, p in zip(out, pan))


def test_missed_samples_are_filled_with_the_court_moved_by_the_camera():
    motion = shifting(91)
    missed = {30, 36, 42}
    loose = {**CONFIG, "review_consistency": 1.0}  # a shifted image is no pinhole camera; the net check does not apply
    shot = register_shot(0, 90, 30.0, SIZE, lambda f: np.zeros((14, 3)) if f in missed else panned(f), loose, motion)
    by_frame = {s["frame"]: s for s in shot["samples"]}
    assert shot["status"] == "ok" and shot["filled"] == 3
    for f in missed:
        assert by_frame[f]["filled"]
        assert np.abs(np.array(by_frame[f]["corners_px"]) - (TRUE_CORNERS + [-3.0 * f, 0])).max() < 1.0
    without = register_shot(0, 90, 30.0, SIZE, lambda f: np.zeros((14, 3)) if f in missed else panned(f), loose)
    assert without["filled"] == 0 and len(without["samples"]) == len(shot["samples"]) - 3


def test_samples_are_not_filled_from_far_away():
    shot = register_shot(0, 600, 30.0, SIZE, lambda f: panned(f) if f < 60 else np.zeros((14, 3)), motion=shifting(601),
                         config={**CONFIG, "min_valid_share": 0.0})
    assert max(s["frame"] for s in shot["samples"]) <= 54 + 5 * 30


def test_a_correction_follows_a_panning_camera():
    from vball.court_registration import apply_corrections
    corners = np.array([[600, 300], [1320, 300], [1700, 800], [220, 800]], float)
    court = {"status": "done", "shots": [{"start_frame": 0, "end_frame": 90, "status": "failed", "error": None, "samples": []}]}
    out = apply_corrections(court, [{"shot": 0, "frame": 30, "points_px": corners.tolist()}], SIZE, motion=shifting(91), fps=30.0)
    assert np.abs(corners_at(out, 60) - (corners + [-90.0, 0])).max() < 1e-6
    assert np.abs(corners_at(out, 0) - (corners + [90.0, 0])).max() < 1e-6
    kp30 = np.array(next(s for s in out["shots"][0]["samples"] if s["frame"] == 30)["keypoints"])
    kp60 = np.array(next(s for s in out["shots"][0]["samples"] if s["frame"] == 60)["keypoints"])
    assert np.allclose(kp60[:, :2], kp30[:, :2] + [-90.0, 0])  # net points move too
