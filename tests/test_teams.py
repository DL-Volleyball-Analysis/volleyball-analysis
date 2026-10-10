import numpy as np
import pandas as pd

from vball.players import roles
from vball.teams import Assignment, assign, colour_hist, on_court_share, torso_crop

COLOURS = {"red": (40, 40, 200), "blue": (200, 60, 30), "black": (20, 20, 20), "yellow": (40, 220, 230)}


def hists(colour, n=5, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        crop = np.clip(np.full((40, 20, 3), COLOURS[colour], float) + rng.normal(0, 12, (40, 20, 3)), 0, 255)
        out.append(colour_hist(crop.astype(np.uint8)))
    return np.stack(out)


def test_two_teams_and_a_referee():
    tracks = {i: hists("red", seed=i) for i in range(6)} | {10 + i: hists("blue", seed=i) for i in range(6)}
    tracks[99] = hists("black")
    a = assign(tracks)
    assert {a[i].team for i in range(6)} == {"a"} or {a[i].team for i in range(6)} == {"b"}
    assert a[0].team != a[10].team and not any(a[i].other for i in list(range(6)) + list(range(10, 16)))
    assert a[99].other and a[99].team is None


def test_similar_shirts_are_not_split_and_nobody_is_marked_other():
    tracks = {i: hists("red", seed=i) for i in range(8)}
    assert not any(x.other for x in assign(tracks).values())


def test_too_few_tracks_are_not_clustered():
    assert assign({1: hists("red"), 2: hists("blue")}) == {1: Assignment(None, False), 2: Assignment(None, False)}


def test_torso_crop_and_court_share():
    frame = np.zeros((200, 200, 3), np.uint8)
    assert torso_crop(frame, (50, 20, 90, 180)).shape == (56, 20, 3)
    assert torso_crop(frame, (0, 0, 5, 5)) is None
    assert on_court_share(np.array([[5.0, 4.0], [9.0, -1.5], [np.nan, np.nan]])) == 0.5


def table(rows):
    """rows: (frame, track_id, conf, placed, court_x, court_y)"""
    df = pd.DataFrame(rows, columns=["frame", "track_id", "conf", "placed", "court_x", "court_y"])
    return df.assign(x1=0.0, y1=0.0, x2=1.0, y2=2.0)


def test_referee_off_court_is_other_but_the_libero_on_court_stays_a_player():
    df = table([(0, 1, 0.9, True, 4.0, 4.0), (0, 2, 0.9, True, 9.0, -1.5), (0, 3, 0.9, True, 3.0, 6.0)])
    out = roles(df, {1: Assignment("a", False), 2: Assignment(None, True), 3: Assignment(None, True)})
    assert out.set_index("track_id")["role"].to_dict() == {1: "player", 2: "other", 3: "player"}
    assert out.set_index("track_id")["team"][1] == "a"


def test_at_most_twelve_players_per_frame_placed_first_then_confident():
    rows = [(0, t, 0.5 + t / 100, t < 10, 4.0, 4.0) for t in range(15)]  # 10 placed, 5 not placed but confident
    out = roles(table(rows))
    players = set(out.loc[out["role"] == "player", "track_id"])
    assert len(players) == 12 and set(range(10)) <= players and players - set(range(10)) == {13, 14}


def test_short_tracks_do_not_shape_the_teams():
    # more spectators (short tracks, many colours) than players: the teams come from the long tracks only
    tracks = {i: hists("red", seed=i) for i in range(6)} | {10 + i: hists("blue", seed=i) for i in range(6)}
    spectators = {100 + i: hists(c, seed=i) for i, c in enumerate(["black", "yellow"] * 8)}
    cover = {t: 0.9 for t in tracks} | {t: 0.05 for t in spectators}
    a = assign(tracks | spectators, cover)
    assert all(a[t].other for t in spectators) and not any(a[t].other for t in tracks)
