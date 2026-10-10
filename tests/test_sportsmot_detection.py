import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_sportsmot_detection", ROOT / "scripts" / "build_sportsmot_detection.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


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
