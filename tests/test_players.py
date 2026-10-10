import numpy as np
import pandas as pd

from vball.players import TrackerConfig, interpolate_tracks, sample_every, track_frames


def fake_step(script):
    """A detector + tracker that returns pre-scripted rows per call, and records calls."""
    calls = []

    def step(image):
        calls.append(int(image[0, 0]))
        return script.get(int(image[0, 0]), [])

    return step, calls


def frames(n):
    return [np.full((4, 4), i, np.uint8) for i in range(n)]  # pixel value = frame number


def test_sampling_rate():
    assert [sample_every(30, 10), sample_every(25, 10), sample_every(30, 30), sample_every(30, 0)] == [3, 2, 1, 1]


def test_detector_runs_on_sampled_frames_only():
    step, calls = fake_step({})
    track_frames(frames(10), src_fps=30, cfg=TrackerConfig(det_fps=10), step=step)
    assert calls == [0, 3, 6, 9]


def test_boxes_are_interpolated_between_samples_and_ids_kept():
    step, _ = fake_step({
        0: [(7, 0, 0, 10, 10, 0.9)],
        3: [(7, 30, 0, 40, 10, 0.6)],
    })
    df = track_frames(frames(4), src_fps=30, cfg=TrackerConfig(det_fps=10), step=step)
    assert df["frame"].tolist() == [0, 1, 2, 3]
    assert set(df["track_id"]) == {7}
    assert df["x1"].tolist() == [0, 10, 20, 30]
    assert df["interpolated"].tolist() == [False, True, True, False]
    assert df.loc[df["interpolated"], "conf"].eq(0.6).all()  # the weaker endpoint


def test_no_extrapolation_and_long_gaps_stay_empty():
    df = pd.DataFrame([
        (2, 1, 0, 0, 1, 1, 0.9, False),
        (4, 1, 2, 0, 3, 1, 0.9, False),
        (20, 1, 18, 0, 19, 1, 0.9, False),
    ], columns=["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"])
    out = interpolate_tracks(df, n_frames=30, max_gap=5)
    assert out["frame"].tolist() == [2, 3, 4, 20]  # nothing before 2 or after 20; 4 -> 20 too long


def test_every_frame_when_detecting_at_full_rate():
    step, calls = fake_step({1: [(3, 0, 0, 1, 1, 0.5)]})
    df = track_frames(frames(3), src_fps=30, cfg=TrackerConfig(det_fps=30), step=step)
    assert calls == [0, 1, 2]
    assert df["frame"].tolist() == [1] and not df["interpolated"].any()


# --- on-court filter and positions (synthetic homography: 50 px per metre, court origin at (100, 600),
# image y grows downwards, so court y goes up the image) ---
import numpy as np  # noqa: E402

from vball.players import place_on_court  # noqa: E402

H_SYN = np.array([[50.0, 0, 100], [0, -50.0, 600], [0, 0, 1]])


def box_at(frame, tid, x_m, y_m):
    """A 40 x 90 px box whose bottom-centre stands at court (x_m, y_m)."""
    u, v = 100 + 50 * x_m, 600 - 50 * y_m
    return {"frame": frame, "track_id": tid, "x1": u - 20, "y1": v - 90, "x2": u + 20, "y2": v,
            "conf": 0.9, "interpolated": False}


def test_referee_outside_the_margins_is_dropped_and_server_behind_the_end_line_kept():
    df = pd.DataFrame([
        box_at(0, 1, 4.5, 4.5),    # player on side A
        box_at(0, 2, 13.0, 2.0),   # player on side B
        box_at(0, 3, -6.0, 4.0),   # server 6 m behind the end line: kept
        box_at(0, 4, 9.0, -4.5),   # first referee beside the post, 4.5 m outside the sideline: dropped
        box_at(0, 5, 9.0, 16.0),   # crowd: dropped
    ])
    out = place_on_court(df, lambda f: H_SYN)
    assert sorted(out["track_id"]) == [1, 2, 3]
    pos = out.set_index("track_id")
    assert pos.loc[1, "side"] == "a" and pos.loc[2, "side"] == "b" and pos.loc[3, "side"] == "a"
    assert abs(pos.loc[3, "court_x"] + 6.0) < 1e-6 and abs(pos.loc[2, "court_y"] - 2.0) < 1e-6
    assert out["placed"].all()


def test_player_on_the_end_line_has_x_near_zero():
    out = place_on_court(pd.DataFrame([box_at(0, 1, 0.0, 3.0)]), lambda f: H_SYN)
    assert abs(out.loc[0, "court_x"]) < 0.05


def test_frames_without_a_court_mapping_are_kept_unplaced():
    df = pd.DataFrame([box_at(0, 1, 4.5, 4.5), box_at(1, 4, 9.0, -4.5), box_at(1, 1, 4.6, 4.5)])
    out = place_on_court(df, lambda f: H_SYN if f == 0 else None)
    frame1 = out[out["frame"] == 1]
    assert len(frame1) == 2  # the referee is not filtered without a mapping
    assert not frame1["placed"].any() and frame1["court_x"].isna().all() and (frame1["side"] == "").all()
    assert out[out["frame"] == 0]["placed"].all()



def test_track_frames_does_not_bridge_a_long_gap():
    # detected at sampled frames 0 and 3, lost, then the same id again at frame 30 (sampling every 3 frames)
    seen = {0: [(1, 0, 0, 10, 10, 0.9)], 3: [(1, 3, 0, 13, 10, 0.9)], 30: [(1, 30, 0, 40, 10, 0.9)]}
    frames = [None] * 31
    calls = iter(sorted(range(0, 31, 3)))
    def step(image):
        return seen.get(next(calls), [])
    cfg = TrackerConfig(det_fps=10)
    df = track_frames(frames, 30.0, cfg, step)
    got = sorted(df["frame"].tolist())
    assert got[:4] == [0, 1, 2, 3]       # the short gap is filled
    assert 15 not in got and 30 in got   # the long gap (27 frames > 3 x 3) is not
