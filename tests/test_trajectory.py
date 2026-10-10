import numpy as np
import pytest

from vball.calibration import look_at
from vball.trajectory import BALL_RADIUS, G, Flight, FlightConfig, FlightFit, fit, reconstruct, segment
from vball.trajectory.synthetic import rally, render

SIZE = (1920, 1080)
CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1600.0, SIZE)
FPS = 50.0
# serve -> receive -> set -> attack to the floor (court metres; side A is x < 9)
TOUCHES = [[-1.0, 7.0, 3.0], [14.5, 3.0, 0.8], [10.0, 5.5, 2.6], [10.5, 1.0, 3.2], [4.0, 6.0, BALL_RADIUS]]
DURATIONS = [1.3, 1.1, 0.9, 0.45]


def true_flights(r):
    return [Flight(a, b) for a, b in zip(r.touches, r.touches[1:])]


def test_render_without_noise_is_the_exact_projection():
    r = render(CAM, TOUCHES, DURATIONS, FPS)
    assert np.allclose(r.uv, CAM.project(r.positions), atol=1e-9)
    assert np.allclose(r.positions[r.touches], TOUCHES, atol=1e-9)


@pytest.mark.parametrize("seed", range(3))
def test_segmentation_cuts_at_the_touches(seed):
    r = render(CAM, TOUCHES, DURATIONS, FPS, noise_px=1.0, seed=seed)
    flights = segment(r.uv)
    assert len(flights) == len(DURATIONS)
    for fl, (a, b) in zip(flights, zip(r.touches, r.touches[1:])):
        assert abs(fl.start - a) <= 2 and abs(fl.end - b) <= 2


def test_a_long_gap_ends_a_flight():
    r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS, occluded=range(30, 40))
    flights = segment(r.uv, FlightConfig(max_gap=6))
    assert [(f.start, f.end) for f in flights] == [(0, 29), (40, r.touches[-1])]


def test_fit_on_a_noisy_serve_arc_is_within_ten_centimetres():
    # a long flight across the view (the spec's synthetic arc); pooled over seeds
    errors = []
    for seed in range(5):
        r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS, noise_px=2.0, seed=seed)
        f = fit(CAM, r.uv, Flight(0, r.touches[-1]), FPS)
        errors.append(np.linalg.norm(f.at(np.arange(len(r.uv))) - r.positions, axis=1))
    assert np.median(np.concatenate(errors)) <= 0.10


@pytest.mark.parametrize("seed", range(5))
def test_reported_depth_uncertainty_covers_the_error(seed):
    # every flight, short and along the line of sight included: the mid-flight error stays within
    # two reported standard deviations (measured worst case over 20 seeds: 1.5)
    r = render(CAM, TOUCHES, DURATIONS, FPS, noise_px=2.0, seed=seed)
    for fl in true_flights(r):
        f = fit(CAM, r.uv, fl, FPS)
        mid = (fl.start + fl.end) // 2
        assert np.linalg.norm(f.at([mid])[0] - r.positions[mid]) <= 2 * f.depth_sd_m


def test_short_fast_attack_is_low_quality():
    r = render(CAM, TOUCHES, DURATIONS, FPS, noise_px=2.0)
    f = fit(CAM, r.uv, true_flights(r)[-1], FPS)
    assert f.quality == "low" and "depth poorly constrained" in f.reasons


def test_occluded_frames_get_positions_from_the_fit():
    hidden = range(20, 25)  # 5 frames in the middle of the serve
    r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS, noise_px=1.0, occluded=hidden)
    out = reconstruct(CAM, r.uv, FPS)
    assert len(out) == 1
    flight = out[0]
    assert not flight["observed"][list(hidden)].any() and flight["observed"].sum() == len(r.uv) - 5
    err = np.linalg.norm(flight["positions"][list(hidden)] - r.positions[list(hidden)], axis=1)
    assert err.max() < 0.15


def test_flight_along_the_line_of_sight_is_low_quality():
    # short, flat flight straight toward the camera: little parallax, little visible curvature
    r = render(CAM, [[9.5, 8.0, 2.0], [9.5, 6.5, 1.9]], [0.25], FPS, noise_px=2.0)
    f = fit(CAM, r.uv, Flight(0, r.touches[-1]), FPS)
    assert f.quality == "low" and "depth poorly constrained" in f.reasons


def test_flight_across_the_view_is_ok():
    r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS, noise_px=2.0)
    f = fit(CAM, r.uv, Flight(0, r.touches[-1]), FPS)
    assert f.quality == "ok" and f.reasons == []


def test_derived_values_match_the_analytic_ones():
    p0, v0 = np.array([2.0, 4.0, 2.5]), np.array([8.0, -1.0, 4.0])
    T = 1.3
    f = FlightFit(0, int(T * FPS), p0, v0, FPS, 0.0, 0.0)
    d = f.derived()
    t_apex = v0[2] / 9.81
    assert d["apex"]["height_m"] == pytest.approx(p0[2] + v0[2] ** 2 / (2 * 9.81))
    assert d["apex"]["t"] == pytest.approx(t_apex)
    t_net = (9.0 - p0[0]) / v0[0]
    assert d["net_crossing"]["height_m"] == pytest.approx(p0[2] + v0[2] * t_net + 0.5 * G[2] * t_net ** 2)
    assert d["net_crossing"]["y_m"] == pytest.approx(p0[1] + v0[1] * t_net)
    assert d["start_speed_mps"] == pytest.approx(np.linalg.norm(v0))
    # floor contact: z(t) = BALL_RADIUS, later root
    a, b, c = 0.5 * G[2], v0[2], p0[2] - BALL_RADIUS
    t_land = (-b - np.sqrt(b * b - 4 * a * c)) / (2 * a)
    assert t_land <= T
    assert d["landing"]["x_m"] == pytest.approx(p0[0] + v0[0] * t_land)


def test_no_landing_when_the_flight_ends_in_the_air():
    f = FlightFit(0, 20, np.array([5.0, 4.0, 2.0]), np.array([3.0, 0.0, 5.0]), FPS, 0.0, 0.0)
    assert f.derived()["landing"] is None



def test_physically_impossible_flights_are_dropped_with_the_reason():
    from vball.trajectory import implausible
    frames = np.arange(0, 20)
    fast = FlightFit(0, 19, np.array([2.0, 4.0, 2.5]), np.array([60.0, 0.0, 2.0]), FPS, 1.0, 0.1)
    assert "start speed" in implausible(fast, fast.at(frames))
    away = FlightFit(0, 19, np.array([2.0, 300.0, 2.5]), np.array([5.0, 0.0, 2.0]), FPS, 1.0, 0.1)
    assert implausible(away, away.at(frames)) == "path leaves the hall"
    normal = FlightFit(0, 19, np.array([2.0, 4.0, 2.5]), np.array([12.0, 0.5, 3.0]), FPS, 1.0, 0.1)
    assert implausible(normal, normal.at(frames)) is None
    # a wrong camera: the true detections refitted through a camera 3x too wide give an impossible path
    r = render(CAM, TOUCHES, DURATIONS, FPS)
    wrong = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1600.0 / 3, SIZE)
    rejected = []
    kept = reconstruct(wrong, r.uv, FPS, rejected=rejected)
    assert rejected and all(len(x) == 3 for x in rejected)
    assert len(kept) + len(rejected) == len(segment(r.uv))


def test_corrupt_respects_the_error_rates():
    from vball.trajectory.synthetic import corrupt
    r = render(CAM, TOUCHES, DURATIONS, FPS)
    uv = corrupt(r.uv, SIZE, miss=0.3, false=0.1, noise_px=2.0, seed=3)
    lost = np.isnan(uv).any(axis=1)
    assert abs(lost.mean() - 0.3) < 0.01
    err = np.linalg.norm(uv[~lost] - r.uv[~lost], axis=1)
    assert abs((err > 30).mean() - 0.1) < 0.03  # replaced by points elsewhere
    assert np.median(err[err < 30]) < 3          # the rest carry only noise
    runs = np.diff(np.flatnonzero(np.diff(np.r_[0, lost.astype(int), 0])))[::2]
    assert np.mean(runs) > 1.5                   # misses come in bursts


def test_touch_players_stand_near_the_touches():
    from vball.trajectory.synthetic import touch_players
    players = touch_players(TOUCHES, seed=1)
    assert players[-1] is None
    assert all(np.linalg.norm(p - np.array(t[:2])) < 1.5 for p, t in zip(players[:-1], TOUCHES[:-1]))


def test_false_detections_inside_a_serve_are_dropped():
    from vball.trajectory.synthetic import corrupt
    errors, dropped = [], 0
    for seed in range(5):
        r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS)
        uv = corrupt(r.uv, SIZE, false=0.10, noise_px=2.0, seed=seed)
        f = fit(CAM, uv, Flight(0, r.touches[-1]), FPS)
        errors.append(np.median(np.linalg.norm(f.at(np.arange(len(uv))) - r.positions, axis=1)))
        dropped += f.dropped
    assert np.median(errors) <= 0.3 and dropped > 0


def test_a_path_in_front_of_the_camera_is_never_drawn_there():
    # a real ballistic path 3 m in front of the camera (something near the lens): the projection is perfect,
    # so only the bounds stop the fit from placing the ball there
    near = [[9.0, -11.0, 6.5], [9.6, -10.5, 6.0]]
    r = render(CAM, near, [0.4], FPS, noise_px=0.5)
    fl = Flight(0, r.touches[-1])
    free = fit(CAM, r.uv, fl, FPS, FlightConfig(bounded=False))
    assert free.p0[1] < -9  # unbounded: in front of the camera
    f = fit(CAM, r.uv, fl, FPS)
    m = FlightConfig().hall_margin_m
    assert f.p0[1] >= -m - 1e-6
    assert f.quality == "low"


def test_player_anchors_halve_the_error_of_short_attacks():
    from vball.trajectory.synthetic import corrupt, touch_players
    plain, anchored = [], []
    for seed in range(10):
        r = render(CAM, TOUCHES, DURATIONS, FPS)
        uv = corrupt(r.uv, SIZE, miss=0.3, false=0.12, noise_px=2.0, seed=seed)
        fl = true_flights(r)[-1]  # the 0.45 s attack
        players = touch_players(TOUCHES, seed=seed)
        frames = np.arange(fl.start, fl.end + 1)
        for out, pat in ((plain, None), (anchored, {"start": [players[-2]], "end": None})):
            f = fit(CAM, uv, fl, FPS, players_at=pat)
            out.append(np.median(np.linalg.norm(f.at(frames) - r.positions[frames], axis=1)))
        assert f.anchors == ["start"]
    assert np.median(anchored) <= 0.5 * np.median(plain)


def test_without_players_a_flight_has_no_anchors():
    r = render(CAM, TOUCHES[:2], DURATIONS[:1], FPS, noise_px=2.0)
    assert fit(CAM, r.uv, Flight(0, r.touches[-1]), FPS).anchors == []
    far = {"start": [np.array([17.0, 8.5])], "end": None}  # nobody near the ball's ray
    assert fit(CAM, r.uv, Flight(0, r.touches[-1]), FPS, players_at=far).anchors == []
