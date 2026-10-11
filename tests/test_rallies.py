import numpy as np

from vball.rallies import RallyConfig, evaluate, iou, read_cvat, segment, smooth

CVAT = """<annotations>
  <image id="10" name="frame_000010"><tag label="serving-start" source="manual"></tag></image>
  <image id="40" name="frame_000040"><tag label="serving-end" source="manual"></tag></image>
  <image id="200" name="frame_000200"><tag label="in-game-end" source="manual"></tag></image>
  <image id="300" name="frame_000300"><tag label="serving-start" source="manual"></tag></image>
  <image id="400" name="frame_000400"><tag label="serving-start" source="manual"></tag></image>
  <image id="600" name="frame_000600"><tag label="in-game-end" source="manual"></tag></image>
  <image id="700" name="frame_000700"></image>
</annotations>"""


def test_cvat_rallies_run_from_serve_start_to_rally_end():
    # the start at 300 has no end before the next start: an unfinished annotation, dropped
    assert read_cvat(CVAT) == [(10, 200), (400, 600)]


def test_cvat_from_a_file(tmp_path):
    p = tmp_path / "13.xml"
    p.write_text(CVAT)
    assert read_cvat(p) == [(10, 200), (400, 600)]


def test_smooth_keeps_the_level_at_the_edges():
    assert np.allclose(smooth(np.ones(7), 3), 1.0)
    assert np.allclose(smooth(np.array([0, 0, 3, 0, 0.0]), 3), [0, 1, 1, 1, 0])


def test_segment_hysteresis_merging_and_minimum_length():
    t = np.arange(0, 60, 0.2)
    p = np.zeros_like(t)
    p[(t >= 5) & (t < 15)] = 0.9          # a rally
    p[(t >= 9) & (t < 10)] = 0.5          # a dip between p_off and p_on: not split
    p[(t >= 15.4) & (t < 20)] = 0.9       # after a 0.4 s gap: merged
    p[(t >= 30) & (t < 31)] = 0.9         # 1 s of play: too short
    p[(t >= 40) & (t < 50)] = 0.8
    r = segment(t, p, RallyConfig(smooth_s=0.2, min_gap_s=1.0, min_rally_s=3.0))
    assert [(round(a, 1), round(b, 1)) for a, b, _ in r] == [(5.0, 19.8), (40.0, 49.8)]
    assert 0.8 < r[0][2] < 0.9 and np.isclose(r[1][2], 0.8)
    assert segment(np.array([]), np.array([])) == []


def test_evaluate_matches_by_iou_one_to_one():
    labelled = [(10, 20), (30, 40), (50, 60)]
    detected = [(10.5, 19, 0.9), (31, 42, 0.8), (31, 39, 0.7), (70, 80, 0.6)]  # two cover the 2nd, one is false
    m = evaluate(detected, labelled)
    assert (m["matched"], m["detected"], m["labelled"]) == (2, 4, 3)
    assert m["precision"] == 0.5 and np.isclose(m["recall"], 2 / 3)
    assert m["start_err_median_s"] == 0.75 and m["end_err_median_s"] == 1.0  # starts 0.5, 1.0; ends 1.0, 1.0
    assert m["within_1s"] == 1.0
    assert iou((0, 10), (5, 15)) == 5 / 15 and evaluate([], labelled)["recall"] == 0


def test_player_motion_in_box_heights():
    import vball.rally_cues as m
    prev = np.array([[0, 0, 10, 100], [200, 0, 210, 100.0]])
    cur = np.array([[50, 0, 60, 100], [200, 0, 210, 100.0]])  # one moved 50 px (half a box height), one stood still
    assert np.isclose(m.player_motion(prev, cur), 0.25)
    assert m.player_motion(np.zeros((0, 4)), cur) == 0.0


def test_ball_summary_share_and_speed():
    import vball.rally_cues as m
    seen, speed = m.ball_summary([(0, 0), (19.2, 0), None, (38.4, 0)], fps=25.0, width=1920)
    assert seen == 0.75 and np.isclose(speed, 0.25)  # 19.2 px per frame = 1% of the width, 25 frames / s
    assert m.ball_summary([], 25.0, 1920) == (0.0, 0.0)


def test_saved_model_detects_rallies(tmp_path):
    import pandas as pd
    from sklearn.ensemble import HistGradientBoostingClassifier

    from vball.rallies import CUES, RallyConfig, detect, features, load_model, save_model
    t = np.arange(0, 60, 0.2)
    play = ((t > 10) & (t < 20)) | ((t > 35) & (t < 45))
    cues = pd.DataFrame({"t": t, **{c: np.where(play, 1.0, 0.0) for c in CUES}})
    f = features(cues, 5.0)
    assert f.shape == (len(t), len(CUES) * 5)  # the cue, mean and std over 1 s and 3 s
    clf = HistGradientBoostingClassifier(max_iter=20).fit(f, play)
    save_model(tmp_path / "m.joblib", clf, RallyConfig(smooth_s=0.2), 5.0, {"note": "test"})
    m = load_model(tmp_path / "m.joblib")
    rallies = detect(m, cues)
    assert [(round(a), round(b)) for a, b, _ in rallies] == [(10, 20), (35, 45)]
    assert detect(m, cues.iloc[:0]) == []
