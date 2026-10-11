import numpy as np

from vball.ball_detect import Candidate, blobs, load, merge, views
from vball.ball_track import TrackConfig, camera_shift, drop_fixed, fill_gaps, link


def test_views_cover_the_frame_with_overlapping_tiles():
    v = views(1920, 1080, (2, 2))
    assert v[0] == (0, 0, 1920, 1080) and len(v) == 5
    tiles = v[1:]
    assert min(x for x, *_ in tiles) == 0 and max(x + w for x, _, w, _ in tiles) == 1920
    assert max(y + h for _, y, _, h in tiles) == 1080
    assert tiles[0][2] > 960  # overlap: wider than half the frame
    assert views(1920, 1080, None) == [(0, 0, 1920, 1080)]


def test_blobs_and_merge():
    hm = np.zeros((288, 512), np.float32)
    hm[100:103, 200:203] = 0.9
    hm[10:12, 10:12] = 0.6
    b = sorted(blobs(hm), key=lambda t: -t[2])
    assert len(b) == 2 and abs(b[0][0] - 201) < 0.01 and abs(b[0][2] - 0.9) < 1e-6
    same_ball = [Candidate(100, 100, 0.7), Candidate(104, 101, 0.9), Candidate(400, 300, 0.6)]
    assert merge(same_ball, 12) == [Candidate(104, 101, 0.9), Candidate(400, 300, 0.6)]


def scene(n=30, pan=4):
    """Textured background panning right by `pan` px per frame, a fixed white dash on the floor, and a bright
    ball moving on its own."""
    rng = np.random.default_rng(0)
    bg = np.kron(rng.integers(0, 200, (50, 113)), np.ones((8, 8)))[:400, :900].astype(np.uint8)  # 8 px texture
    frames, ball = [], []
    for i in range(n):
        f = np.ascontiguousarray(np.roll(bg, -pan * i, axis=1)[:, :600])
        dash_x = 300 - pan * i
        f[200:204, dash_x:dash_x + 8] = 255
        bx, by = 50 + 15 * i, 100 + 2 * i
        f[by - 5:by + 6, bx - 5:bx + 6] = 255  # an 11 px ball
        frames.append(f)
        ball.append((bx, by, dash_x + 4))
    return frames, ball


def test_camera_shift_follows_a_pan():
    frames, _ = scene(pan=4)
    s = camera_shift(frames)
    assert abs(s[10][0] - (-40)) < 2 and abs(s[10][1]) < 2


def test_fixed_objects_are_dropped_and_the_ball_kept():
    frames, ball = scene()
    cands = [[Candidate(bx, by, 0.8), Candidate(dx, 202, 0.9)] for bx, by, dx in ball]
    kept = drop_fixed(frames, cands)
    inner = kept[5:-5]
    assert all(len(c) == 1 and c[0].x == ball[i + 5][0] for i, c in enumerate(inner))


def test_link_prefers_a_consistent_path_over_a_stronger_jump():
    cfg = TrackConfig()
    cands = [[Candidate(100 + 10 * i, 200, 0.7)] for i in range(10)]
    cands[5].append(Candidate(900, 50, 0.95))   # a confident detection far away (crowd, ad board)
    cands[7] = []                               # one missed frame
    path = link(cands, width=1920, cfg=cfg)
    assert path[5].x == 150 and path[7] is None and path[9].x == 190


def test_link_allows_a_new_ball_after_a_long_gap():
    cands = [[Candidate(100, 100, 0.8)]] * 3 + [[]] * 20 + [[Candidate(1500, 600, 0.8)]] * 3
    path = link(cands, width=1920)
    assert path[-1] is not None and path[-1].x == 1500


def test_fill_gaps_follows_a_parabola_and_leaves_long_gaps():
    t = np.arange(20, dtype=float)
    xy = np.stack([10 * t, 0.5 * (t - 10) ** 2], axis=1)
    xy[8:11] = np.nan       # short gap: filled
    xy[14:20] = np.nan      # trailing: not a gap between detections
    out, filled = fill_gaps(xy)
    assert filled[8:11].all() and not filled[14:].any()
    assert np.allclose(out[8:11, 0], 10 * t[8:11], atol=1e-6) and np.allclose(out[8:11, 1], 0.5 * (t[8:11] - 10) ** 2, atol=1e-6)
    long = np.stack([t, t], 1)
    long[3:12] = np.nan
    assert not fill_gaps(long)[1].any()


def test_unknown_detector_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        load("tracknet9")


def test_a_low_contrast_ball_in_flight_is_kept():
    """Gym footage: the ball barely differs from the background (motion below min_motion) but never stays put."""
    frames, ball = scene()
    dim = [np.clip(f.astype(int) // 4 + 60, 0, 255).astype(np.uint8) for f in frames]  # low contrast everywhere
    cands = [[Candidate(bx, by, 0.8)] for bx, by, _ in ball]
    kept = drop_fixed(dim, cands, TrackConfig(min_motion=1000.0))  # every patch counts as "barely changing"
    assert all(len(c) == 1 for c in kept)
