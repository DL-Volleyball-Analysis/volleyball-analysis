
from vball.datasets import sportsmot_detection as b


def test_mot_boxes_become_normalised_yolo_lines_clipped_to_the_image():
    lines = b.mot_to_yolo([(100, 50, 40, 120), (1260, 700, 40, 40), (1300, 10, 20, 20)], 1280, 720).splitlines()
    assert lines[0] == "0 0.093750 0.152778 0.031250 0.166667"
    assert lines[1] == "0 0.992188 0.986111 0.015625 0.027778"  # clipped at the right and bottom edges
    assert len(lines) == 2                                       # fully outside: dropped
    assert b.mot_to_yolo([], 1280, 720) == ""


def test_validation_holds_out_whole_match_videos():
    assert b.video_of("v_Dk3EpDDa3o0_c007") == "v_Dk3EpDDa3o0"
    valid = [s for s in b.VOLLEYBALL_TRAIN if b.video_of(s) in b.VALID_VIDEOS]
    train_videos = {b.video_of(s) for s in b.VOLLEYBALL_TRAIN} - b.VALID_VIDEOS
    assert len(valid) == 2 and len(b.VOLLEYBALL_TRAIN) == 15 and not (train_videos & b.VALID_VIDEOS)


def test_build_writes_every_third_frame_with_yolo_labels(tmp_path):
    import cv2
    import numpy as np
    seq = tmp_path / "src" / "v_x_c001"
    (seq / "gt").mkdir(parents=True)
    (seq / "img1").mkdir()
    (seq / "seqinfo.ini").write_text("[Sequence]\nimWidth=100\nimHeight=50\nimExt=.jpg\nseqLength=4\n")
    (seq / "gt" / "gt.txt").write_text("1,1,10,10,20,20,1,1,1\n4,1,0,0,10,10,1,1,1\n")
    for f in range(1, 5):
        cv2.imwrite(str(seq / "img1" / f"{f:06d}.jpg"), np.zeros((50, 100, 3), np.uint8))
    counts = b.build(tmp_path / "src", tmp_path / "out", ["v_x_c001"], every=3)
    assert counts == {"train": 2, "valid": 0}
    assert (tmp_path / "out" / "train" / "labels" / "v_x_c001_000001.txt").read_text() == "0 0.200000 0.400000 0.200000 0.400000\n"
    assert "nc: 1" in (tmp_path / "out" / "data.yaml").read_text()
    try:
        b.build(tmp_path / "src", tmp_path / "out", ["missing"])
    except SystemExit as e:
        assert "missing" in str(e)
