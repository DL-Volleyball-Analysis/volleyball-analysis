from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball.datasets import ball_clips as bbc


def test_labels_follow_the_letterbox():
    xy = np.array([[640.0, 360.0], [0.0, 0.0], [1280.0, 720.0]])
    vis = np.array([True, False, True])
    p = bbc.to_input(xy, vis, 1280, 720)  # 16:9: a plain 0.4 scale
    assert np.allclose(p, [[256, 144], [-1, -1], [512, 288]])
    sq = bbc.to_input(np.array([[50.0, 50.0]]), np.array([True]), 100, 100)  # square: letterboxed, centred
    assert np.allclose(sq, [[256, 144]])


def fake_sources(tmp: Path):
    vb_videos, vb_ann = tmp / "vb" / "videos", tmp / "vb" / "ann"
    for match, clip in ((4, 100), (1, 200)):  # 4 is a test match, 1 a training match
        d = vb_videos / str(match) / str(clip)
        d.mkdir(parents=True)
        for f in range(clip - 2, clip + 3):
            cv2.imwrite(str(d / f"{f}.jpg"), np.full((720, 1280, 3), 100, np.uint8))
        (vb_ann / str(match)).mkdir(parents=True, exist_ok=True)
        np.savetxt(vb_ann / str(match) / f"{clip}.txt", [[640, 360], [0, 0], [10, 20], [30, 40], [50, 60]], fmt="%d")
    orel = tmp / "orel"
    for split, match, stem in (("train", "match3", "a"), ("test", "match8", "b"), ("train", "20250623_beach", "c")):
        (orel / "data" / split / match / "csv").mkdir(parents=True)
        (orel / "data" / split / match / "video").mkdir(parents=True)
        v = cv2.VideoWriter(str(orel / "data" / split / match / "video" / f"{stem}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 180))
        for _ in range(4):
            v.write(np.full((180, 320, 3), 80, np.uint8))
        v.release()
        pd.DataFrame({"Frame": range(4), "Visibility": [1, 0, 1, 1], "X": [160, -1, 0, 320], "Y": [90, -1, 0, 180]}).to_csv(
            orel / "data" / split / match / "csv" / f"{stem}_ball.csv", index=False)
    return (vb_videos, vb_ann), orel


def test_build_splits_by_match_and_writes_input_frames(tmp_path):
    vb, orel = fake_sources(tmp_path)
    m = bbc.build(tmp_path / "out", vb, orel)
    assert set(zip(m.source, m.match, m.split)) == {("volleyball", "4", "test"), ("volleyball", "1", "train"),
                                                    ("orel", "match3", "test"), ("orel", "match8", "train")}  # beach left out
    clip = tmp_path / "out" / m.loc[m.source == "orel", "folder"].iloc[0]
    assert len(list(clip.glob("*.jpg"))) == 4 and cv2.imread(str(clip / "00000.jpg")).shape == (288, 512, 3)
    lab = pd.read_csv(clip / "labels.csv")
    assert lab.visible.tolist() == [1, 0, 1, 1] and np.allclose(lab.loc[0, ["x", "y"]], [256, 144])
    assert m.loc[m.source == "volleyball", "visible"].tolist() == [4, 4]
    assert (tmp_path / "out" / "manifest.csv").exists()



def test_orel_without_the_data_folder_and_never_predictions(tmp_path):
    _, orel = fake_sources(tmp_path)
    flat = tmp_path / "flat"
    (orel / "data").rename(flat)  # Kaggle's copy: train/ and test/ at the top
    pred = flat / "train" / "match3" / "csv" / "a_predict_ball.csv"
    pred.write_text((flat / "train" / "match3" / "csv" / "a_ball.csv").read_text())
    (flat / "train" / "match3" / "video" / "a_predict.mp4").write_bytes((flat / "train" / "match3" / "video" / "a.mp4").read_bytes())
    clips = [c[1] for c in bbc.orel_clips(flat)]
    assert sorted(clips) == ["a", "b"]  # the beach match left out, the prediction file ignored
