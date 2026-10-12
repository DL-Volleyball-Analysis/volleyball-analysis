import cv2
import numpy as np
import pytest

from vball import scorebug
from vball.scorebug import Score, changes, parse, step


def test_parse_reads_the_score_and_ignores_the_rotations():
    assert parse("~~ 76 (1) 01-01 (0) 72") == Score(1, 1, 1, 0)
    assert parse("74 (1) 06 - 04 (0) Z5") == Score(1, 6, 4, 0)
    assert parse("(1) 08 05 (0)") == Score(1, 8, 5, 0)  # the hyphen lost, points zero-padded
    assert parse("no score here") is None and parse(None) is None


def test_a_step_is_one_point_or_a_new_set():
    s = Score(1, 6, 4, 0)
    assert step(s, Score(1, 7, 4, 0)) == ("a", False)
    assert step(s, Score(1, 6, 5, 0)) == ("b", False)
    assert step(s, Score(1, 8, 4, 0)) is None  # two points: a misread
    assert step(s, Score(1, 6, 3, 0)) is None  # backwards
    assert step(Score(1, 24, 22, 0), Score(2, 0, 0, 0)) == ("a", True)
    assert step(Score(1, 22, 25, 0), Score(1, 0, 0, 1)) == ("b", True)


def test_changes_need_two_equal_readings_and_drop_misreads():
    S = Score
    readings = [(0, S(1, 6, 4, 0)), (1, S(1, 6, 4, 0)), (2, S(1, 8, 4, 0)), (3, S(1, 6, 4, 0)), (4, None),
                (5, S(1, 7, 4, 0)), (6, S(1, 7, 4, 0)), (7, S(1, 7, 4, 0)), (8, S(1, 7, 5, 0)), (9, S(1, 7, 5, 0))]
    out = changes(readings)
    assert [(c.t, c.team, c.score) for c in out] == [(5, "a", S(1, 7, 4, 0)), (8, "b", S(1, 7, 5, 0))]  # first read


def test_a_set_change_is_a_point_for_the_set_winner():
    S = Score
    out = changes([(0, S(0, 24, 20, 0)), (1, S(0, 24, 20, 0)), (2, S(1, 0, 0, 0)), (3, S(1, 0, 0, 0))])
    assert len(out) == 1 and out[0].team == "a" and out[0].new_set


@pytest.mark.skipif(not scorebug.available(), reason="Tesseract is not installed")
def test_reading_a_drawn_score_bug():
    frame = np.full((720, 1280, 3), 40, np.uint8)
    cv2.putText(frame, "Z4 (1) 06-04 (0) Z5", (450, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    assert scorebug.read(frame) == Score(1, 6, 4, 0)


def test_unreadable_stretches_re_anchor_without_inventing_points():
    S = Score
    readings = [(0, S(1, 5, 0, 0)), (1, S(1, 5, 0, 0)), (70, S(1, 9, 6, 0)), (75, S(1, 9, 6, 0)),
                (80, S(1, 10, 6, 0)), (85, S(1, 10, 6, 0)), (90, S(0, 3, 3, 1)), (91, S(0, 3, 3, 1))]
    missed = []
    out = changes(readings, missed)
    assert [(c.t, c.team) for c in out] == [(80, "a")]  # the backwards reading at 90 s is dropped
    assert missed == [(70, 10)]
