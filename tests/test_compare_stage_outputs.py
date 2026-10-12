import json

import numpy as np
import pandas as pd

from vball.pipeline.compare import compare, json_diff


def write(folder, court=1.0, rows=(1.0, 2.0), extra=False):
    folder.mkdir(parents=True)
    (folder / "court.json").write_text(json.dumps({"version": "6", "shots": [{"score": court, "status": "ok"}]}))
    pd.DataFrame({"frame": [0, 1], "x": list(rows)}).to_csv(folder / "ball.csv", index=False)
    np.savez(folder / "camera_motion.npz", steps=np.eye(3)[None])
    if extra:
        (folder / "extra.json").write_text("{}")


def test_identical_folders(tmp_path):
    write(tmp_path / "a" / "clip")
    write(tmp_path / "b" / "clip")
    assert compare(tmp_path / "a", tmp_path / "b") == {}


def test_reports_value_table_and_missing_differences(tmp_path):
    write(tmp_path / "a" / "clip")
    write(tmp_path / "b" / "clip", court=1.5, rows=(1.0, 3.0), extra=True)
    d = compare(tmp_path / "a", tmp_path / "b")
    assert d["clip/court.json"] == ["/shots[0]/score: 1.0 != 1.5"]
    assert d["clip/ball.csv"][0].startswith("column x: 1 cells differ")
    assert d["clip/extra.json"] == ["only in second"]


def test_json_numbers_within_tolerance_and_types():
    assert json_diff({"a": 1.0}, {"a": 1.0 + 1e-12}, 1e-9) == []
    assert json_diff([1, 2], [1], 1e-9) == [": length 2 != 1"]
    assert json_diff({"a": True}, {"a": 1}, 1e-9) == ["/a: True != 1"]
