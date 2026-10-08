"""Player statistics from coach tags: attack efficiency, kill rate, aces and serve errors.

A tag is an attack or a serve at a video time, by a team ("a" / "b") and a player number, with an
optional outcome set by the user. Tags are keyed by time, not by rally: each tag counts in the rally that
contains its time, else the nearest rally within MAX_GAP_S, else none (outside rallies, not counted).

Outcomes (`outcomes`): the user's outcome wins; otherwise the last tag of a rally takes it from the
rally's effective winner (tagged team won: kill / ace, lost: error; no winner: unknown) and earlier tags
are in play.

Statistics (`summarise`), per player and per team, for each set and the match:
  attack efficiency = (kills - errors) / decided, kill rate = kills / decided, where decided = attempts
  whose outcome is known (an unknown outcome is not a miss); None when nothing is decided;
  serves, aces, serve errors; `unknown` counts tags whose outcome is unknown (the row is incomplete).
Team rows sum the player counts and recompute the ratios; ratios are never averaged.
"""
from dataclasses import dataclass

MAX_GAP_S = 2.0
ATTACK_OUTCOMES = ("kill", "error", "in_play")
SERVE_OUTCOMES = ("ace", "error", "in_play")


@dataclass(frozen=True)
class Tag:
    id: str
    time_s: float
    kind: str                   # "attack" | "serve"
    team: str                   # "a" | "b"
    number: int
    outcome: str | None = None  # set by the user; None = infer

    def __post_init__(self):
        if self.kind not in ("attack", "serve"):
            raise ValueError(f"kind must be 'attack' or 'serve', got {self.kind!r}")
        if self.team not in ("a", "b"):
            raise ValueError(f"team must be 'a' or 'b', got {self.team!r}")
        allowed = ATTACK_OUTCOMES if self.kind == "attack" else SERVE_OUTCOMES
        if self.outcome is not None and self.outcome not in allowed:
            raise ValueError(f"{self.kind} outcome must be one of {allowed}, got {self.outcome!r}")


@dataclass(frozen=True)
class Rally:
    idx: int
    start_s: float
    end_s: float
    winner: str | None  # effective winner (correction first)
    set_no: int


@dataclass(frozen=True)
class TagResult:
    tag: Tag
    rally: int | None  # rally idx, None when outside rallies
    outcome: str       # kill / error / in_play / ace / unknown / "outside"
    inferred: bool     # True when not set by the user


def rally_of(time_s: float, rallies: list[Rally], max_gap_s: float = MAX_GAP_S) -> Rally | None:
    best, best_gap = None, None
    for r in rallies:
        gap = 0.0 if r.start_s <= time_s <= r.end_s else min(abs(time_s - r.start_s), abs(time_s - r.end_s))
        if gap <= max_gap_s and (best_gap is None or gap < best_gap):
            best, best_gap = r, gap
    return best


def outcomes(tags: list[Tag], rallies: list[Rally], max_gap_s: float = MAX_GAP_S) -> list[TagResult]:
    """Effective outcome of every tag, in the order given."""
    by_rally: dict[int, list[Tag]] = {}
    where: dict[str, Rally | None] = {}
    for t in tags:
        r = rally_of(t.time_s, rallies, max_gap_s)
        where[t.id] = r
        if r is not None:
            by_rally.setdefault(r.idx, []).append(t)
    last = {idx: max(ts, key=lambda t: (t.time_s, t.id)).id for idx, ts in by_rally.items()}

    out = []
    for t in tags:
        r = where[t.id]
        if r is None:
            out.append(TagResult(t, None, "outside", t.outcome is None))
        elif t.outcome is not None:
            out.append(TagResult(t, r.idx, t.outcome, False))
        elif last[r.idx] != t.id:
            out.append(TagResult(t, r.idx, "in_play", True))
        elif r.winner is None:
            out.append(TagResult(t, r.idx, "unknown", True))
        else:
            won = r.winner == t.team
            out.append(TagResult(t, r.idx, ("kill" if t.kind == "attack" else "ace") if won else "error", True))
    return out


@dataclass
class Line:
    team: str
    number: int | None  # None for the team total
    set_no: int | None  # None for the whole match
    attempts: int = 0
    kills: int = 0
    attack_errors: int = 0
    serves: int = 0
    aces: int = 0
    serve_errors: int = 0
    unknown: int = 0          # tags (attacks and serves) with an unknown outcome
    unknown_attacks: int = 0

    @property
    def decided(self) -> int:
        return self.attempts - self.unknown_attacks

    @property
    def efficiency(self) -> float | None:
        return (self.kills - self.attack_errors) / self.decided if self.decided else None

    @property
    def kill_rate(self) -> float | None:
        return self.kills / self.decided if self.decided else None

    @property
    def incomplete(self) -> bool:
        return self.unknown > 0

    def add(self, res: TagResult) -> None:
        if res.tag.kind == "attack":
            self.attempts += 1
            self.kills += res.outcome == "kill"
            self.attack_errors += res.outcome == "error"
            self.unknown_attacks += res.outcome == "unknown"
        else:
            self.serves += 1
            self.aces += res.outcome == "ace"
            self.serve_errors += res.outcome == "error"
        self.unknown += res.outcome == "unknown"

    def as_dict(self) -> dict:
        return {"team": self.team, "number": self.number, "set_no": self.set_no, "attempts": self.attempts,
                "kills": self.kills, "attack_errors": self.attack_errors, "efficiency": self.efficiency,
                "kill_rate": self.kill_rate, "serves": self.serves, "aces": self.aces,
                "serve_errors": self.serve_errors, "unknown": self.unknown, "incomplete": self.incomplete}


def summarise(results: list[TagResult], rallies: list[Rally]) -> list[Line]:
    """Lines per (team, player) and per team, for each set and the match. Tags outside rallies are skipped.
    Order: team, then players by number before the team total, each with its sets then the match line."""
    set_of = {r.idx: r.set_no for r in rallies}
    lines: dict[tuple, Line] = {}

    def line(team, number, set_no):
        key = (team, number, set_no)
        if key not in lines:
            lines[key] = Line(team, number, set_no)
        return lines[key]

    for res in results:
        if res.rally is None:
            continue
        s = set_of[res.rally]
        for number in (res.tag.number, None):
            for set_no in (s, None):
                line(res.tag.team, number, set_no).add(res)

    def order(key):
        team, number, set_no = key
        return (team, number is None, number or 0, set_no is None, set_no or 0)

    return [lines[k] for k in sorted(lines, key=order)]


CSV_HEADER = ["team", "number", "name", "set", "attempts", "kills", "attack_errors", "efficiency",
              "kill_rate", "serves", "aces", "serve_errors", "unknown"]


def csv_rows(lines: list[Line], names: dict[tuple[str, int], str] | None = None) -> list[list]:
    """Rows for a CSV file (header first): one per player and set, the player's match row, team totals."""
    names = names or {}

    def ratio(x):
        return "" if x is None else f"{x:.3f}"

    rows = [CSV_HEADER]
    for ln in lines:
        rows.append([ln.team.upper(), "TOTAL" if ln.number is None else ln.number,
                     "" if ln.number is None else names.get((ln.team, ln.number), ""),
                     "match" if ln.set_no is None else ln.set_no, ln.attempts, ln.kills, ln.attack_errors,
                     ratio(ln.efficiency), ratio(ln.kill_rate), ln.serves, ln.aces, ln.serve_errors, ln.unknown])
    return rows
