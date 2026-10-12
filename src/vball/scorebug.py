"""Point labels from the on-screen score bug (change label-rallies-from-score).

Matches filmed by a fixed camera and published with a score bug (VolleyballWatchdog: "Z4 (1) 06-04 (0) Z5" at the top
of the frame: rotation, sets won, points, points, sets won, rotation) say when every point ended and who won it:

1. `read`: the bug's crops (SCOREBUGS, fractions of the frame, tried in turn) scaled to TEXT_PX high, made dark-on-light two ways
   in turn (Otsu, or the light unsaturated text pixels when the bug has no box behind it), Tesseract (`--psm 7`,
   digits and "()-" only), and the pattern "(s) pp-pp (s)" -> Score.
2. `changes`: readings once per second, cleaned. A score counts when read the same twice in a row, and must move the
   match forward from the last counted one: one team +1 point, or a new set (one team's sets +1, points back to 0-0).
   Anything else is a misread and dropped, except a score read REANCHOR_READS times in a row that is several points
   ahead (the bug was unreadable for a while): the sequence re-anchors there and those points are counted as missed,
   not invented. Each reading is the majority over the crops and binarisations.
   Each step forward is a point change with its time and scoring team.

Tesseract is a local binary (brew install tesseract); `available()` says whether it is there.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

SCOREBUGS = {"watchdog": [(0.0, 0.040, 0.28, 0.72), (0.0, 0.056, 0.28, 0.72)]}  # y0, y1, x0, x1 (fractions
# of the frame), tried in turn: the tighter crop leaves out the serve marker under one score, which confuses Tesseract
TEXT_PX = 120  # the crop is scaled to this height before reading
REANCHOR_READS = 5  # readings in a row before a jump of several points is accepted
PATTERN = re.compile(r"\((\d)\)\s*(\d{1,2})\s*-\s*(\d{1,2})\s*\((\d)\)|\((\d)\)\s*(\d{2})\s*(\d{2})\s*\((\d)\)")


@dataclass(frozen=True)
class Score:
    sets_a: int
    points_a: int
    points_b: int
    sets_b: int


@dataclass(frozen=True)
class Change:
    t: float  # seconds: when the new score was first read (counted once read twice in a row)
    team: str  # "a" (left in the bug) or "b"
    score: Score  # the score after the point
    new_set: bool  # the point that won a set (the bug resets to 0-0)


def available() -> bool:
    return shutil.which("tesseract") is not None


def parse(text: str) -> Score | None:
    m = PATTERN.search(text or "")
    if not m:
        return None
    g = [x for x in m.groups() if x is not None]  # second form: two-digit points with the hyphen lost
    return Score(*(int(x) for x in g))


def crop(frame: np.ndarray, bug: str = "watchdog", k: int = 0) -> np.ndarray:
    y0, y1, x0, x1 = SCOREBUGS[bug][k]
    h, w = frame.shape[:2]
    return frame[int(y0 * h) : max(int(y1 * h), int(y0 * h) + 1), int(x0 * w) : int(x1 * w)]


def _binarised(c: np.ndarray) -> list[np.ndarray]:
    """Dark-on-light versions of the crop to try in turn: Otsu on grey (a bug with a box behind its text), and the
    light, unsaturated text pixels (a bug drawn straight over the stands)."""
    g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    if otsu.mean() < 128:
        otsu = 255 - otsu
    hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)
    return [otsu, _characters(((hsv[..., 2] > 170) & (hsv[..., 1] < 80)).astype(np.uint8))]


def _characters(mask: np.ndarray) -> np.ndarray:
    """Keep the connected parts of a text mask shaped like characters (30-95% of the crop's height, at most 1.5x as
    wide as tall, clear of the top and bottom edges): white seats and boards beside the bug go. Dark on light."""
    h = mask.shape[0]
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    y, bh, bw = st[:, 1], st[:, 3], st[:, 2]
    keep = (bh >= 0.3 * h) & (bh <= 0.95 * h) & (bw <= 1.5 * bh) & (y > 0) & (y + bh < h)
    # parentheses and the hyphen: thin or short parts next to characters
    keep |= (bh >= 0.02 * h) & (bh < 0.3 * h) & (bw <= 0.5 * h) & (y > 0.2 * h) & (y + bh < 0.8 * h)
    keep[0] = False
    return np.where(keep[lab], 0, 255).astype(np.uint8)


def _tesseract(img: np.ndarray) -> str:
    ok, png = cv2.imencode(".png", img)
    if not ok:
        return ""
    out = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789()-"],
        input=png.tobytes(),
        capture_output=True,
        check=False,
    )
    return out.stdout.decode(errors="ignore")


def read(frame: np.ndarray, bug: str = "watchdog") -> Score | None:
    """The score shown in a frame, or None when it cannot be read (replays, graphics, no bug)."""
    votes = []
    for k in range(len(SCOREBUGS[bug])):
        c = crop(frame, bug, k)
        f = TEXT_PX / max(c.shape[0], 1)
        c = cv2.resize(c, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        votes += [x for x in (parse(_tesseract(img)) for img in _binarised(c)) if x is not None]
    if not votes:
        return None
    return max(votes, key=votes.count)  # the majority over crops and binarisations; ties go to the first read


def step(prev: Score, new: Score) -> tuple[str, bool] | None:
    """(team, new_set) when `new` follows `prev` by one point, else None."""
    if (new.sets_a, new.sets_b) == (prev.sets_a, prev.sets_b):
        if (new.points_a, new.points_b) == (prev.points_a + 1, prev.points_b):
            return "a", False
        if (new.points_a, new.points_b) == (prev.points_a, prev.points_b + 1):
            return "b", False
        return None
    if (new.points_a, new.points_b) == (0, 0):
        if (new.sets_a, new.sets_b) == (prev.sets_a + 1, prev.sets_b):
            return "a", True
        if (new.sets_a, new.sets_b) == (prev.sets_a, prev.sets_b + 1):
            return "b", True
    return None


def ahead(prev: Score, new: Score) -> int:
    """How many points `new` is ahead of `prev` when it plausibly follows it after unreadable stretches (same set and
    no team's points going down, or later sets); 0 when it does not."""
    if (new.sets_a, new.sets_b) == (prev.sets_a, prev.sets_b):
        da, db = new.points_a - prev.points_a, new.points_b - prev.points_b
        return da + db if da >= 0 and db >= 0 else 0
    if new.sets_a >= prev.sets_a and new.sets_b >= prev.sets_b:
        return new.points_a + new.points_b + 1  # at least the set point and the new set's points
    return 0


def changes(readings: list[tuple[float, Score | None]], missed: list | None = None) -> list[Change]:
    """Point changes from (time, score or None) readings in time order (see module doc). A score read twice that is
    several points ahead (the bug unreadable for a while) re-anchors the sequence without inventing the points in
    between; their count is appended to `missed` as (time, points)."""
    out: list[Change] = []
    counted: Score | None = None
    last: Score | None = None
    since, run = 0.0, 0  # since: set by the first reading
    for t, s in readings:
        if s is None:
            continue
        if s != last:
            last, since, run = s, t, 1  # when this score was first read
            continue
        run += 1
        if counted is None:
            counted = s
            continue
        if s == counted:
            continue
        st = step(counted, s)
        if st is not None:
            out.append(Change(since, st[0], s, st[1]))
            counted = s
        elif ahead(counted, s) > 1 and run >= REANCHOR_READS:  # a jump must hold, or one misread could take over
            if missed is not None:
                missed.append((since, ahead(counted, s)))
            counted = s
    return out


def read_video(
    video: Path, every_s: float = 1.0, bug: str = "watchdog", tick=lambda frac: None
) -> list[tuple[float, Score | None]]:
    """(time, score) once every `every_s` seconds, reading frames as a stream."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step_frames = max(1, int(round(fps * every_s)))
    out, i = [], 0
    while True:
        if i % step_frames == 0:
            ok, frame = cap.read()
            if not ok:
                break
            out.append((round(i / fps, 2), read(frame, bug)))
            if total:
                tick(i / total)
        elif not cap.grab():
            break
        i += 1
    cap.release()
    return out
