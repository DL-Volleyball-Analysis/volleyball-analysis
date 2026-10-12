"""Point labels from the on-screen score bug (change label-rallies-from-score).

Matches filmed by a fixed camera and published with a score bug (VolleyballWatchdog: "Z4 (1) 06-04 (0) Z5" at the top
of the frame: rotation, sets won, points, points, sets won, rotation) say when every point ended and who won it:

1. `read`: the bug's crop (SCOREBUGS, fractions of the frame), grey, 2x upscale, Otsu threshold, Tesseract (`--psm 7`,
   digits and "()-" only), and the pattern "(s) pp-pp (s)" -> Score.
2. `changes`: readings once per second, cleaned. A score counts when read the same twice in a row, and must move the
   match forward from the last counted one: one team +1 point, or a new set (one team's sets +1, points back to 0-0).
   Anything else is a misread and dropped. Each step forward is a point change with its time and scoring team.

Tesseract is a local binary (brew install tesseract); `available()` says whether it is there.
"""
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

SCOREBUGS = {"watchdog": (0.0, 0.056, 0.28, 0.72)}  # y0, y1, x0, x1 as fractions of the frame
PATTERN = re.compile(r"\((\d)\)\s*(\d{1,2})\s*-\s*(\d{1,2})\s*\((\d)\)")


@dataclass(frozen=True)
class Score:
    sets_a: int
    points_a: int
    points_b: int
    sets_b: int


@dataclass(frozen=True)
class Change:
    t: float        # seconds: when the new score was first read
    team: str       # "a" (left in the bug) or "b"
    score: Score    # the score after the point
    new_set: bool   # the point that won a set (the bug resets to 0-0)


def available() -> bool:
    return shutil.which("tesseract") is not None


def parse(text: str) -> Score | None:
    m = PATTERN.search(text or "")
    return Score(*(int(x) for x in m.groups())) if m else None


def crop(frame: np.ndarray, bug: str = "watchdog") -> np.ndarray:
    y0, y1, x0, x1 = SCOREBUGS[bug]
    h, w = frame.shape[:2]
    return frame[int(y0 * h):max(int(y1 * h), int(y0 * h) + 1), int(x0 * w):int(x1 * w)]


def read(frame: np.ndarray, bug: str = "watchdog") -> Score | None:
    """The score shown in a frame, or None when it cannot be read (replays, graphics, no bug)."""
    g = cv2.cvtColor(crop(frame, bug), cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    if g.mean() < 128:  # dark text on light: Tesseract prefers it
        g = 255 - g
    ok, png = cv2.imencode(".png", g)
    if not ok:
        return None
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789()-"],
                         input=png.tobytes(), capture_output=True, check=False)
    return parse(out.stdout.decode(errors="ignore"))


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


def changes(readings: list[tuple[float, Score | None]]) -> list[Change]:
    """Point changes from (time, score or None) readings in time order (see module doc)."""
    out, counted, last = [], None, None
    for t, s in readings:
        if s is None:
            continue
        stable = s == last
        last = s
        if not stable:
            continue
        if counted is None:
            counted = s
            continue
        if s == counted:
            continue
        st = step(counted, s)
        if st is not None:
            out.append(Change(t, st[0], s, st[1]))
            counted = s
    return out


def read_video(video: Path, every_s: float = 1.0, bug: str = "watchdog",
               tick=lambda frac: None) -> list[tuple[float, Score | None]]:
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
