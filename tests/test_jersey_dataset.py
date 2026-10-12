from vball.datasets import jersey_crops as b


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
    assert (
        b.split_of("japan_poland") == "test"
        and b.split_of("usm_usach_1") == "valid"
        and b.split_of("graz_1") == "train"
    )


def test_no_match_is_in_two_splits():
    assert not (b.SPLIT["test"] & b.SPLIT["valid"])


def test_build_keeps_digit_crops_split_by_match(tmp_path, monkeypatch):
    import yaml

    sources = []
    for name, img_name in (
        ("set-a", "japan_poland_raw_out_1_jpg.rf.x.jpg"),
        ("set-b", "graz_1_cutted_f1_jpg.rf.y.jpg"),
    ):
        src = tmp_path / name
        (src / "train" / "images").mkdir(parents=True)
        (src / "train" / "labels").mkdir(parents=True)
        (src / "data.yaml").write_text(yaml.safe_dump({"names": ["Player", "7"]}))
        (src / "README.roboflow.txt").write_text("CC BY 4.0")
        (src / "train" / "images" / img_name).write_bytes(b"jpg")
        (src / "train" / "labels" / f"{img_name[:-4]}.txt").write_text("0 .5 .5 .2 .2\n1 .4 .4 .1 .1\n")
        (src / "train" / "images" / "notes.txt").write_text("not an image")
        sources.append(src)
    monkeypatch.setattr(b, "SOURCES", tuple(sources))
    monkeypatch.setattr(b, "TRAIN_ONLY", {"set-b"})
    out = b.build(tmp_path / "out")
    assert out["images"] == {"test": 1, "train": 1}
    assert out["test"][7] == 1 and out["train"][7] == 1
    assert (tmp_path / "out" / "LICENSE_set-a.txt").exists()
