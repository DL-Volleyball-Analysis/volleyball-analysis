import pandas as pd

from vball.actions import ActionConfig, assign, events

STEP = 3  # frames between action samples (30 fps video, 10 fps actions)


def tracks(*rows):
    """rows: (frame, track_id, x1, y1, x2, y2)"""
    return pd.DataFrame(rows, columns=["frame", "track_id", "x1", "y1", "x2", "y2"])


def dets(*rows):
    """rows: (frame, action, conf, x1, y1, x2, y2)"""
    return pd.DataFrame(rows, columns=["frame", "action", "conf", "x1", "y1", "x2", "y2"])


PLAYER_7 = (100, 100, 200, 300)
PLAYER_9 = (400, 100, 500, 300)
TRACKS = tracks(*[(f, tid, *box) for f in range(0, 60, STEP) for tid, box in ((7, PLAYER_7), (9, PLAYER_9))])


def test_a_spike_over_several_samples_is_one_event_for_that_track():
    d = dets(*[(f, "spike", 0.8, 105, 95, 205, 290) for f in (12, 15, 18, 21)])
    (ev,) = events(d, TRACKS, STEP)
    assert (ev.action, ev.track_id, ev.start_frame, ev.end_frame, ev.samples) == ("spike", 7, 12, 21, 4)


def test_the_box_goes_to_the_track_it_overlaps_most():
    d = dets((30, "block", 0.9, 390, 100, 495, 300))
    assert assign(d, TRACKS)["track_id"].tolist() == [9]


def test_a_box_without_a_player_is_reported_without_one():
    d = dets((30, "serve", 0.9, 700, 100, 800, 300), (33, "serve", 0.9, 702, 100, 802, 300))
    (ev,) = events(d, TRACKS, STEP)
    assert ev.track_id is None and ev.samples == 2


def test_unassigned_boxes_far_apart_are_separate_events():
    d = dets((30, "receive", 0.9, 700, 100, 800, 300), (33, "receive", 0.9, 1500, 100, 1600, 300))
    assert len(events(d, TRACKS, STEP)) == 2


def test_a_long_pause_starts_a_new_event():
    gap = (ActionConfig().max_gap + 1) * STEP
    d = dets((12, "set", 0.8, *PLAYER_7), (12 + gap, "set", 0.8, *PLAYER_7))
    assert [e.start_frame for e in events(d, TRACKS, STEP)] == [12, 12 + gap]


def test_events_below_the_peak_threshold_are_dropped():
    d = dets((12, "spike", 0.5, *PLAYER_7), (15, "spike", 0.55, *PLAYER_7), (30, "spike", 0.7, *PLAYER_9))
    assert [(e.track_id, e.peak_conf) for e in events(d, TRACKS, STEP)] == [(9, 0.7)]


def test_two_players_acting_at_once_give_two_events():
    d = dets((12, "block", 0.9, *PLAYER_7), (12, "block", 0.8, *PLAYER_9), (15, "block", 0.9, *PLAYER_7))
    evs = events(d, TRACKS, STEP)
    assert sorted((e.track_id, e.samples) for e in evs) == [(7, 2), (9, 1)]


def test_no_tracks_at_all_still_gives_events():
    d = dets((12, "serve", 0.9, *PLAYER_7))
    (ev,) = events(d, tracks(), STEP)
    assert ev.track_id is None
