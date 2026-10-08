"""Rally winners -> running score under indoor rules.

A set is won at 25 points (15 in the deciding set) with a 2-point lead; the match is best of 5.
Teams are "a" / "b" (teams, not court sides: teams change ends between sets).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    set_no: int     # set this rally belongs to (1-based)
    a: int          # points in that set after the rally
    b: int
    sets_a: int     # sets won after the rally (includes the set this rally ended)
    sets_b: int
    set_over: bool  # this rally ended the set


def set_target(set_no: int, best_of: int = 5) -> int:
    return 15 if set_no == best_of else 25


def running_score(winners, best_of: int = 5) -> list[Score]:
    """Score after each rally. A None winner (not decided yet) leaves the score unchanged."""
    out = []
    set_no, a, b, sets_a, sets_b = 1, 0, 0, 0, 0
    for w in winners:
        if w == "a":
            a += 1
        elif w == "b":
            b += 1
        elif w is not None:
            raise ValueError(f"winner must be 'a', 'b' or None, got {w!r}")
        over = max(a, b) >= set_target(set_no, best_of) and abs(a - b) >= 2
        if over:
            sets_a, sets_b = sets_a + (a > b), sets_b + (b > a)
        out.append(Score(set_no, a, b, sets_a, sets_b, over))
        if over:
            set_no, a, b = set_no + 1, 0, 0
    return out
