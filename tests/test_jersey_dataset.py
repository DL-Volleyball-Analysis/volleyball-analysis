import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_jersey_dataset", ROOT / "scripts" / "build_jersey_dataset.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def test_classes_are_mapped_by_name_not_index():
    # the capstone bug: index 0 of a dataset whose classes are ['Ball', 'Player', 'number'] became digit 0
    assert [b.digit_of(n) for n in ["Ball", "Player", "number"]] == [None, None, None]
    assert b.digit_of("7") == 7 and b.digit_of(" 0 ") == 0 and b.digit_of("cero") == 0 and b.digit_of("n") is None


def test_non_digit_boxes_are_dropped_and_digits_renumbered():
    text = "0 .5 .5 .1 .1\n1 .2 .2 .1 .1\n2 .3 .3 .1 .1\n"
    assert b.relabel(text, {0: None, 1: None, 2: 4}) == "4 .3 .3 .1 .1\n"
    assert b.relabel("0 .5 .5 .1 .1\n", {0: None}) == ""


def test_frames_are_grouped_by_match():
    assert b.match_of("chile_usa_cutted_f0_id2_jpg.rf.81398a.jpg") == "chile_usa"
    assert b.match_of("graz_1-2_cutted_f6896_id3_jpg.rf.x.jpg") == "graz_1"  # a second part of the same match
    assert b.match_of("poland_italy_raw_out_14_2_jpg.rf.x.jpg") == "poland_italy"
    assert b.match_of("usm_ucen_2_full_raw_out_3_1_jpg.rf.x.jpg") == "usm_ucen_2_full"
    assert b.split_of("japan_poland") == "test" and b.split_of("usm_usach_1") == "valid" and b.split_of("graz_1") == "train"


def test_no_match_is_in_two_splits():
    assert not (b.SPLIT["test"] & b.SPLIT["valid"])
