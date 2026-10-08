from vball.scoring import running_score


def test_points_and_unknown_winner():
    s = running_score(["a", None, "b", "a"])
    assert [(x.a, x.b) for x in s] == [(1, 0), (1, 0), (1, 1), (2, 1)]
    assert not any(x.set_over for x in s)


def test_set_needs_two_point_lead():
    s = running_score(["a", "b"] * 24 + ["a", "a", "b"])
    assert (s[-3].a, s[-3].b, s[-3].set_over) == (25, 24, False)
    assert (s[-2].a, s[-2].b, s[-2].set_over, s[-2].sets_a) == (26, 24, True, 1)
    assert (s[-1].set_no, s[-1].a, s[-1].b) == (2, 0, 1)


def test_deciding_set_to_15():
    s = running_score(["a"] * 25 * 2 + ["b"] * 25 * 2 + ["a"] * 15)
    assert (s[-1].set_no, s[-1].a, s[-1].sets_a, s[-1].sets_b, s[-1].set_over) == (5, 15, 3, 2, True)
