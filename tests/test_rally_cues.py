import cv2
import numpy as np

from vball import rally_cues


class FakeYOLO:
    """Stands in for ultralytics.YOLO: 'court' models return nothing, the player model 7 boxes."""

    overrides = {"imgsz": 640}

    def __init__(self, weights):
        self.weights = weights

    def __call__(self, frame, **kw):
        class Boxes:
            def __len__(self):
                return 7

        class Result:
            boxes = Boxes()

        return [Result()]


def test_quick_check_reads_a_few_frames_spread_over_the_video(tmp_path, monkeypatch):
    path = tmp_path / "clip.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (160, 90))
    for _ in range(100):
        w.write(np.full((90, 160, 3), 90, np.uint8))
    w.release()
    import sys
    import types

    fake = types.ModuleType("ultralytics")  # CI does not install ultralytics; the test needs only its YOLO name
    fake.YOLO = FakeYOLO
    monkeypatch.setitem(sys.modules, "ultralytics", fake)
    monkeypatch.setattr(rally_cues, "detect_court", lambda model, frame, sz: np.zeros((14, 3)))
    df = rally_cues.quick_check(path, n=10)
    assert list(df.columns) == rally_cues.COLUMNS and len(df) == 10
    assert df.t.iloc[0] == 0 and df.t.iloc[-1] > 3.5  # spread over the 4 s clip
    assert (df.players == 7).all() and (df.court_ok == 0).all()
    from vball.rallies import outside_training

    assert outside_training(df)  # no court: out of training, told without a full pass


def test_stage_cues_from_ball_and_people():
    import pandas as pd

    # court metres -> image: 50 px per metre, no perspective (enough for the cue arithmetic)
    H = np.array([[50.0, 0, 100], [0, 50.0, 100], [0, 0, 1]])
    fps, n = 10.0, 40
    ball = pd.DataFrame(
        {
            "frame": np.arange(n),
            "visible": (np.arange(n) < 20).astype(int),
            "x": 500.0 + 10 * np.arange(n),
            "y": 400.0 - 5 * np.arange(n),
        }
    )

    def box(xm, ym):  # a person standing at court (xm, ym): feet at the box's bottom centre
        u, v = 100 + 50 * xm, 100 + 50 * ym
        return [u - 10, v - 80, u + 10, v]

    rows = []
    for f in (0, 5, 10, 15, 20, 25, 30, 35):
        shift = 0.1 * f  # everyone walks 1 m/s along the court
        people = [
            (3 + shift, 2),
            (5 + shift, 6),
            (12, 3),
            (14, 7),
            (-3, 4.5),
        ]  # the last one serves from behind the end line
        rows += [(f, *box(x, y)) for x, y in people]
    people = pd.DataFrame(rows, columns=["frame", "x1", "y1", "x2", "y2"])
    cues = rally_cues.stage_cues(ball, people, fps, n, (1280, 720), H, rate=2.0)
    assert list(cues.columns) == rally_cues.STAGE_COLUMNS and len(cues) == 8
    first, late = cues.iloc[1], cues.iloc[-1]
    assert first.ball_seen == 1.0 and late.ball_seen == 0.0
    assert abs(first.ball_speed - np.hypot(100, 50) / 1280) < 1e-3 and first.ball_rise > 0
    assert first.on_court == 4 and first.both_sides == 2 and first.behind_end == 1
    assert 0.3 < first.player_speed < 1.1  # two walk 1 m/s, two stand still: the median between
    assert (rally_cues.stage_cues(ball, people, fps, n, (1280, 720), None, rate=2.0).on_court == 0).all()
