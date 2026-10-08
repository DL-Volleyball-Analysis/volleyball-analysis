import pytest

from vball.stats import Rally, Tag, csv_rows, outcomes, rally_of, summarise

# fixture match, hand-calculated below: set 1 = rallies 0-3, set 2 = rally 4
RALLIES = [
    Rally(0, 0, 10, "a", 1), Rally(1, 12, 20, "b", 1), Rally(2, 22, 30, "a", 1),
    Rally(3, 32, 40, None, 1), Rally(4, 50, 60, "b", 2),
]
TAGS = [
    Tag("t1", 1.0, "serve", "a", 7),                    # r0, not last -> in play
    Tag("t2", 8.0, "attack", "a", 10),                  # r0 last, A won -> kill
    Tag("t3", 12.5, "serve", "b", 3),                   # r1, not last -> in play
    Tag("t4", 15.0, "attack", "a", 10),                 # r1 last, B won -> error
    Tag("t5", 25.0, "attack", "a", 10, outcome="error"),  # r2, set by the user
    Tag("t6", 28.0, "attack", "a", 4),                  # r2 last, A won -> kill
    Tag("t7", 35.0, "attack", "a", 10),                 # r3 last, no winner -> unknown
    Tag("t8", 50.5, "serve", "b", 3),                   # r4 last, B won -> ace
    Tag("t9", 45.0, "attack", "a", 4),                  # 5 s from any rally -> outside
]


def results():
    return {r.tag.id: r for r in outcomes(TAGS, RALLIES)}


def lines():
    return {(ln.team, ln.number, ln.set_no): ln for ln in summarise(outcomes(TAGS, RALLIES), RALLIES)}


def test_outcomes_follow_the_rules():
    res = results()
    assert {k: v.outcome for k, v in res.items()} == {
        "t1": "in_play", "t2": "kill", "t3": "in_play", "t4": "error", "t5": "error", "t6": "kill",
        "t7": "unknown", "t8": "ace", "t9": "outside"}
    assert res["t5"].inferred is False and res["t2"].inferred is True
    assert res["t9"].rally is None


def test_last_attack_of_a_won_rally_is_a_kill_and_follows_a_corrected_winner():
    tag = [Tag("x", 5.0, "attack", "a", 9)]
    assert outcomes(tag, [Rally(0, 0, 10, "a", 1)])[0].outcome == "kill"
    assert outcomes(tag, [Rally(0, 0, 10, "b", 1)])[0].outcome == "error"


def test_user_outcome_takes_precedence_over_the_winner():
    tag = [Tag("x", 5.0, "attack", "a", 9, outcome="in_play")]
    assert outcomes(tag, [Rally(0, 0, 10, "a", 1)])[0].outcome == "in_play"


def test_tag_counts_in_the_rally_that_now_contains_its_time():
    # re-analysis moved the boundary: the tag at 11 s now falls in the second rally
    tag = [Tag("x", 11.0, "attack", "b", 2)]
    before = [Rally(0, 0, 11.5, "a", 1), Rally(1, 14, 20, "b", 1)]
    after = [Rally(0, 0, 10.5, "a", 1), Rally(1, 10.8, 20, "b", 1)]
    assert outcomes(tag, before)[0].rally == 0
    assert outcomes(tag, after)[0].rally == 1


def test_nearest_rally_within_two_seconds():
    rallies = [Rally(0, 0, 10, "a", 1), Rally(1, 20, 30, "b", 1)]
    assert rally_of(11.5, rallies).idx == 0
    assert rally_of(18.5, rallies).idx == 1
    assert rally_of(15.0, rallies) is None


def test_hand_calculated_player_and_team_lines():
    L = lines()
    a10 = L[("a", 10, None)]
    assert (a10.attempts, a10.kills, a10.attack_errors, a10.unknown) == (4, 1, 2, 1)
    # the unknown attempt is not a miss: ratios over the 3 decided attempts
    assert a10.efficiency == pytest.approx(-1 / 3) and a10.kill_rate == pytest.approx(1 / 3)
    assert a10.incomplete
    assert L[("a", 4, None)].attempts == 1 and L[("a", 4, None)].efficiency == pytest.approx(1.0)  # t9 not counted
    team_a = L[("a", None, None)]
    assert (team_a.attempts, team_a.kills, team_a.attack_errors, team_a.serves) == (5, 2, 2, 1)
    assert team_a.efficiency == pytest.approx(0.0)  # (2 - 2) / 4 decided
    b3 = L[("b", 3, None)]
    assert (b3.serves, b3.aces, b3.serve_errors) == (2, 1, 0)
    assert (L[("b", 3, 1)].serves, L[("b", 3, 1)].aces) == (1, 0)
    assert (L[("b", 3, 2)].serves, L[("b", 3, 2)].aces) == (1, 1)
    assert ("a", 10, 2) not in L  # no tags in set 2


def test_efficiency_and_kill_rate():
    rallies = [Rally(i, 10 * i, 10 * i + 5, None, 1) for i in range(10)]
    outs = ["kill"] * 4 + ["error"] * 2 + ["in_play"] * 4
    tags = [Tag(f"t{i}", 10 * i + 1, "attack", "a", 5, outcome=o) for i, o in enumerate(outs)]
    ln = [x for x in summarise(outcomes(tags, rallies), rallies) if x.number == 5 and x.set_no is None][0]
    assert ln.efficiency == pytest.approx(0.2) and ln.kill_rate == pytest.approx(0.4)
    assert not ln.incomplete


def test_undecided_rally_gives_empty_ratios_and_incomplete():
    rallies = [Rally(0, 0, 10, None, 1)]
    ln = summarise(outcomes([Tag("x", 5, "attack", "a", 9)], rallies), rallies)[0]
    assert ln.attempts == 1 and ln.unknown == 1 and ln.incomplete
    assert ln.efficiency is None and ln.kill_rate is None and ln.as_dict()["efficiency"] is None


def test_no_attempts_means_empty_ratios_not_zero():
    rallies = [Rally(0, 0, 10, "a", 1)]
    ln = summarise(outcomes([Tag("x", 1, "serve", "a", 7)], rallies), rallies)[0]
    assert ln.attempts == 0 and ln.efficiency is None


def test_two_set_csv_export():
    rows = csv_rows(summarise(outcomes(TAGS, RALLIES), RALLIES), names={("b", 3): "Chen"})
    header, body = rows[0], rows[1:]
    assert header[:4] == ["team", "number", "name", "set"]
    b3 = [r for r in body if r[0] == "B" and r[1] == 3]
    assert [r[3] for r in b3] == [1, 2, "match"] and b3[0][2] == "Chen"
    totals = [r for r in body if r[1] == "TOTAL"]
    assert {(r[0], r[3]) for r in totals} == {("A", 1), ("A", "match"), ("B", 1), ("B", 2), ("B", "match")}
    a10_match = [r for r in body if r[0] == "A" and r[1] == 10 and r[3] == "match"][0]
    assert a10_match[7:9] == ["-0.333", "0.333"]
    assert [r for r in body if r[0] == "A" and r[1] == 7][0][7] == ""  # no attempts: empty, not 0


def test_invalid_tags_are_rejected():
    with pytest.raises(ValueError):
        Tag("x", 1, "block", "a", 1)
    with pytest.raises(ValueError):
        Tag("x", 1, "serve", "a", 1, outcome="kill")
