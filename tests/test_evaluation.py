"""vball.evaluation: the evaluation drivers on small synthetic inputs (the real data stays local)."""
import json
import pickle
import types

import numpy as np
import pandas as pd
import pytest

from vball.actors import ActorConfig
from vball.evaluation import actions_volleyball as av
from vball.evaluation import fixed_rallies as fr
from vball.evaluation import player_tracking as pt
from vball.rallies import RallyConfig


# --- fixed-camera rallies -------------------------------------------------------------------------------------------
def match_cues(n_rallies: int, seed: int) -> tuple[pd.DataFrame, list[float]]:
    """Cues at fr.RATE with play for 8 s every 20 s; the bug changes fr.DELAY_S after each rally end."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, 20.0 * n_rallies + 10, 1 / fr.RATE)
    play = ((t % 20) >= 4) & ((t % 20) < 12) & (t < 20 * n_rallies)
    cues = pd.DataFrame({c: rng.normal(0, 0.3, len(t)) + 2.0 * play for c in fr.COLUMNS})
    cues.insert(0, "t", t)
    cues["shot"] = 0
    changes = [20.0 * k + 12 + fr.DELAY_S for k in range(n_rallies)]
    return cues, changes


@pytest.fixture
def matches(tmp_path):
    cues_dir, labels_dir = tmp_path / "cues", tmp_path / "labels"
    cues_dir.mkdir()
    labels_dir.mkdir()
    for k, name in enumerate(("m1", "m2")):
        cues, changes = match_cues(6, k)
        cues.to_csv(cues_dir / f"{name}.csv", index=False)
        (labels_dir / f"{name}.json").write_text(json.dumps({"changes": [{"t": c} for c in changes]}))
    pd.DataFrame().to_csv(cues_dir / "empty.csv", index=False)  # a match without an ok court
    (labels_dir / "empty.json").write_text(json.dumps({"changes": [{"t": 5.0}]}))
    (cues_dir / "unlabelled.csv").write_text("t\n0\n")
    cues.to_csv(cues_dir / "unread.csv", index=False)  # score bug read in too few frames
    (labels_dir / "unread.json").write_text(json.dumps({"read_share": 0.26, "changes": [{"t": 5.0}]}))
    return fr.load(cues_dir, labels_dir)


def test_load_keeps_labelled_matches_with_cues(matches):
    assert sorted(matches) == ["m1", "m2"]
    assert len(matches["m1"][1]) == 6


def test_trained_model_finds_the_rallies_of_another_match(matches):
    model = fr.fit({"m1": matches["m1"]})
    res = fr.evaluate(model, {"m2": matches["m2"]}, RallyConfig(smooth_s=1.0, p_on=0.5, p_off=0.5, min_rally_s=2.0))
    assert res["recall"] >= 0.8 and res["precision"] >= 0.8
    assert res["per_match"]["m2"]["median_delay_s"] == pytest.approx(fr.DELAY_S, abs=1.0)


def test_choose_config_picks_from_the_grid(matches, monkeypatch):
    monkeypatch.setattr(fr, "GRID", fr.GRID[:3])
    assert fr.choose_config(matches) in fr.GRID
    assert fr.choose_config({"m1": matches["m1"]}) in fr.GRID  # one match: scored on itself


# --- actions on the Volleyball dataset ------------------------------------------------------------------------------
class BoxInfo:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def write_annotations(path, monkeypatch):
    """One test-split clip (match 4, key frame 100), two players: a setter and a standing player."""
    mod = types.ModuleType("boxinfo")
    mod.BoxInfo = BoxInfo
    BoxInfo.__module__, BoxInfo.__qualname__ = "boxinfo", "BoxInfo"
    monkeypatch.setitem(__import__("sys").modules, "boxinfo", mod)
    frames = {f: [BoxInfo(player_ID=0, box=(10, 10, 50, 90), category="setting", frame_ID=f),
                  BoxInfo(player_ID=1, box=(100, 10, 140, 90), category="standing", frame_ID=f)] for f in range(96, 105)}
    path.write_bytes(pickle.dumps({"4": {"100": {"category": "r_set", "frame_boxes_dct": frames}}}))


def test_annotations_load_as_plain_boxes_and_refuse_other_classes(tmp_path, monkeypatch):
    p = tmp_path / "annot_all.pkl"
    write_annotations(p, monkeypatch)
    ann = av.load_annotations(p)
    box, label = ann[4][100]["frames"][100][0]
    assert label == "setting" and np.allclose(box, [10, 10, 50, 90])
    bad = tmp_path / "bad.pkl"
    bad.write_bytes(pickle.dumps(types.SimpleNamespace(x=1)))
    with pytest.raises(pickle.UnpicklingError):
        av.load_annotations(bad)


def test_predictions_and_f1_on_a_detected_setter(tmp_path, monkeypatch):
    p = tmp_path / "annot_all.pkl"
    write_annotations(p, monkeypatch)
    ann = av.load_annotations(p)
    set_id = av.ACTIONS.index("set")
    dets = {f"4/100/{f}": [[set_id, 0.9, 10, 10, 50, 90]] for f in range(96, 105)}
    pairs = av.predictions(ann, dets, [4], ActorConfig(top_n=1, threshold=0.3), key_only=True)
    assert sorted(pairs, key=str) == sorted([("set", "set"), (None, None)], key=str)
    s = av.f1s(pairs)
    assert s["set"]["f1"] == 1.0 and s["serve_predictions"] == 0


def test_tune_chooses_on_the_validation_matches(tmp_path, monkeypatch):
    p = tmp_path / "annot_all.pkl"
    write_annotations(p, monkeypatch)
    ann = av.load_annotations(p)
    monkeypatch.setattr(av, "VAL_MATCHES", [4])
    set_id = av.ACTIONS.index("set")
    dets = {f"4/100/{f}": [[set_id, 0.9, 10, 10, 50, 90]] for f in range(96, 105)}
    score, cfg = av.tune(ann, dets, key_only=True)
    assert score > 0 and isinstance(cfg, ActorConfig)


def test_ball_positions_from_labels_and_from_a_detector(tmp_path):
    (tmp_path / "4").mkdir()
    xy = np.zeros((41, 2))
    xy[20] = (30, 40)
    np.savetxt(tmp_path / "4" / "100.txt", xy)
    balls = av.ball_at(tmp_path, 4, 100)
    assert balls[80] is None and np.allclose(balls[100], (30, 40))
    pd.DataFrame({"match": 4, "clip": 100, "x": np.arange(41.0), "y": 5.0, "visible": [i % 2 for i in range(41)]}).to_csv(
        tmp_path / "pred.csv", index=False)
    det = av.detected_ball(tmp_path / "pred.csv")[(4, 100)]
    assert det[80] is None and np.allclose(det[81], (1, 5))


# --- player tracking on SportsMOT -----------------------------------------------------------------------------------
@pytest.fixture
def sportsmot(tmp_path, monkeypatch):
    root = tmp_path / "sportsmot"
    seq = root / "val" / "v_a_c001"
    (seq / "gt").mkdir(parents=True)
    (seq / "img1").mkdir()
    (seq / "seqinfo.ini").write_text("[Sequence]\nframeRate=25\nseqLength=3\n")
    (seq / "gt" / "gt.txt").write_text("1,1,10,20,30,40,1,1,1\n2,1,12,20,30,40,1,1,1\n3,1,14,20,30,40,1,1,1\n")
    (root / "val.txt").write_text("v_a_c001\nv_b_c001\n")
    (root / "volleyball.txt").write_text("v_a_c001\n")
    monkeypatch.setattr(pt, "SPORTSMOT", root)
    monkeypatch.setattr(pt, "GT_ROOT", root / "val")
    monkeypatch.setattr(pt, "RESULTS", tmp_path / "results")
    return root


def test_volleyball_sequences_and_their_info(sportsmot):
    assert pt.volleyball_val_seqs() == ["v_a_c001"]
    assert pt.seq_info("v_a_c001") == (25.0, 3)


def test_ground_truth_as_tracker_is_cut_to_max_frames(sportsmot):
    pt.gt_as_tracker(["v_a_c001"], "gt", max_frames=2)
    rows = pd.read_csv(pt.RESULTS / "gt" / "data" / "v_a_c001.txt", header=None)
    assert len(rows) == 2 and (rows[6] == 1.0).all()


def test_tracker_output_in_mot_format(sportsmot, monkeypatch):
    import cv2
    for f in range(1, 4):
        cv2.imwrite(str(sportsmot / "val" / "v_a_c001" / "img1" / f"{f:06d}.jpg"), np.zeros((8, 8, 3), np.uint8))
    monkeypatch.setattr(pt, "ultralytics_step", lambda cfg: lambda image: [])

    def track_frames(frames, src_fps, cfg, step):
        rows = [(i, 3, 10.0, 20.0, 40.0, 60.0, 0.9, False) for i, img in enumerate(frames) if step(img) is not None]
        return pd.DataFrame(rows, columns=["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"])

    monkeypatch.setattr(pt, "track_frames", track_frames)
    ms = pt.run_tracker(["v_a_c001"], pt.TrackerConfig(), "fake", max_frames=None)
    assert set(ms) == {"v_a_c001"}
    rows = pd.read_csv(pt.RESULTS / "fake" / "data" / "v_a_c001.txt", header=None)
    assert rows.iloc[0, :6].tolist() == [1, 1, 10.0, 20.0, 30.0, 40.0]  # 1-based frame and id, width and height


def test_evaluate_and_classifier_reports(tmp_path, monkeypatch):
    p = tmp_path / "annot_all.pkl"
    write_annotations(p, monkeypatch)
    monkeypatch.setattr(av, "VAL_MATCHES", [4])
    monkeypatch.setattr(av, "TEST_MATCHES", [4])
    set_id = av.ACTIONS.index("set")
    (tmp_path / "dets.json").write_text(json.dumps({f"4/100/{f}": [[set_id, 0.9, 10, 10, 50, 90]] for f in range(96, 105)}))
    (tmp_path / "ann" / "4").mkdir(parents=True)
    xy = np.zeros((41, 2))
    xy[16:25] = (30, 50)  # the ball at the setter's hands
    np.savetxt(tmp_path / "ann" / "4" / "100.txt", xy)
    pd.DataFrame({"match": 4, "clip": 100, "x": 30.0, "y": 50.0, "visible": 1}, index=range(41)).to_csv(tmp_path / "balls.csv", index=False)
    args = types.SimpleNamespace(pkl=p, dets=tmp_path / "dets.json", ann=tmp_path / "ann", ball_preds=tmp_path / "balls.csv",
                                 out=tmp_path / "eval.json")
    av.evaluate(args)
    out = json.loads((tmp_path / "eval.json").read_text())
    assert set(out) == {"key frame", "9 frames", "+ ball (labelled)", "+ ball (detected)"}
    assert out["key frame"]["test"]["set"]["f1"] == 1.0

    pd.DataFrame({"crop": ["4_100_100_0", "4_100_100_1"], "label": ["setting", "standing"],
                  "setting": [0.8, 0.3], "standing": [0.2, 0.7]}).to_csv(tmp_path / "probs.csv", index=False)
    args = types.SimpleNamespace(pkl=p, probs=tmp_path / "probs.csv", ann=tmp_path / "ann", k=2.0, floor=0.6,
                                 ball_preds=[tmp_path / "balls.csv"], out=tmp_path / "cls.json")
    av.classifier(args)
    cls = json.loads((tmp_path / "cls.json").read_text())
    assert cls["classifier"]["set"]["f1"] == 1.0 and len(cls) == 3
