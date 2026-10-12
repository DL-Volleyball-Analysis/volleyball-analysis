import pickle
import sys
import types
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def fake_dataset(tmp: Path) -> tuple[Path, Path]:
    """Two matches (1: train, 4: test), one clip each, two players: a setter and a standing player."""
    boxinfo = types.ModuleType("boxinfo")

    class BoxInfo:
        def __init__(self, **kw):
            self.__dict__.update(kw)
    BoxInfo.__module__, BoxInfo.__qualname__ = "boxinfo", "BoxInfo"  # pickled as boxinfo.BoxInfo, like the real file
    boxinfo.BoxInfo = BoxInfo
    sys.modules["boxinfo"] = boxinfo
    data = {}
    for m, clip in ((1, 100), (4, 200)):
        frames = {}
        for f in range(clip - 4, clip + 5):
            frames[f] = [BoxInfo(player_ID=0, box=(10, 10, 50, 90), category="setting", frame_ID=f),
                         BoxInfo(player_ID=1, box=(100, 10, 140, 90), category="standing", frame_ID=f)]
            d = tmp / "videos" / str(m) / str(clip)
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{f}.jpg"), np.full((120, 200, 3), 128, np.uint8))
        data[str(m)] = {str(clip): {"category": "r_set", "frame_boxes_dct": frames}}
    pkl = tmp / "annot_all.pkl"
    pkl.write_bytes(pickle.dumps(data))
    del sys.modules["boxinfo"]
    return tmp / "videos", pkl


def test_crops_follow_the_match_split_and_thin_standing(tmp_path):
    from vball.datasets import volleyball_actions as b
    videos, pkl = fake_dataset(tmp_path)
    counts = b.build(videos, pkl, tmp_path / "out", margin=0.15, standing_share=0.2)
    assert counts[("train", "setting")] == 5            # key frame and +-2, +-4
    assert counts.get(("train", "standing"), 0) == 1    # 20% of the split: 0.2 / 0.8 x 5 = 1
    assert counts[("test", "setting")] == 1 and counts[("test", "standing")] == 1  # test: key frame, all players
    img = cv2.imread(str(next((tmp_path / "out" / "test" / "setting").glob("*.jpg"))))
    assert img.shape[:2] == (102, 102)  # 40 x 80 box widened by 15% each side (52 x 102, clipped at the top), padded square
