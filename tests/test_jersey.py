from vball.jersey import label, reading, vote


def test_two_digits_side_by_side_read_left_to_right():
    # the 0 is detected first (higher confidence) but sits on the right
    assert reading([(0, 0.9, 60, 10, 90, 60), (1, 0.8, 20, 12, 50, 62)]) == "10"


def test_a_single_digit():
    assert reading([(7, 0.9, 20, 10, 50, 60)]) == "7"


def test_digits_not_side_by_side_keep_the_most_confident():
    # a 3 on the shirt and a stray 8 far below (e.g. on the shorts)
    assert reading([(3, 0.9, 20, 10, 50, 60), (8, 0.7, 25, 150, 55, 200)]) == "3"


def test_unconfident_digits_are_ignored_and_none_left_is_no_reading():
    assert reading([(4, 0.3, 20, 10, 50, 60)]) is None
    assert reading([]) is None
    assert reading([(2, 0.9, 20, 10, 50, 60), (9, 0.2, 60, 10, 90, 60)]) == "2"


def test_at_most_two_digits():
    digits = [(1, 0.9, 10, 10, 30, 60), (2, 0.8, 35, 10, 55, 60), (3, 0.6, 60, 10, 80, 60)]
    assert reading(digits) == "12"


def test_clear_vote():
    v = vote(["10", "10", "10", "16", None, "10"])
    assert (v.number, v.readings, round(v.share, 2)) == (10, 5, 0.8)


def test_unclear_vote_gives_no_number():
    v = vote(["10", "16", "10", "16", "1"])
    assert v.number is None and v.readings == 5


def test_too_few_readings_give_no_number():
    assert vote(["7", "7"]).number is None
    assert vote([None, None]).readings == 0


def test_label_shows_the_number_or_the_tracking_id():
    assert label(12, 7) == "#7" and label(12, None) == "ID 12"


def test_a_label_follows_an_identity_switch():
    from vball.jersey import number_at, segments
    # a track reads 27 for 4 s, then the tracker jumps to a player whose number is not visible (no readings), then 14
    frames = list(range(0, 100, 12)) + list(range(150, 230, 12))
    readings = ["27"] * len(range(0, 100, 12)) + [None, None, None] + ["14"] * (len(range(150, 230, 12)) - 3)
    segs = segments(frames, readings, window=25)
    assert segs[0][2] == 27 and segs[-1][2] == 14
    assert number_at(segs, 40, reach=6) == 27 and number_at(segs, 220, reach=6) == 14
    assert number_at(segs, 160, reach=6) is None  # unread stretch: tracking id, never the old number
    assert number_at(segs, 500, reach=6) is None
