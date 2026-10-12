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
