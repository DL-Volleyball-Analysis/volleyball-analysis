"""Import the evaluation clips and give them placeholder rallies for UI work.

Ball tracking on these clips is real (the worker runs the pipeline). Rally segmentation and
scoring do not exist yet, so the rallies here are synthetic, stored with source='demo', and the
UI labels them as demo data.

Usage: python backend/demo.py
"""
import random

import numpy as np
from vball.paths import VIDEOS
from vball.trajectory import BALL_RADIUS, G, FlightFit

from database import Database
from settings import DB_PATH

REASONS = ("in", "in", "in", "out", "net", "fault")


def demo_rallies(duration_s: float, rng: random.Random) -> list[dict]:
    n = max(2, int(duration_s // 2))
    edges = [duration_s * k / n for k in range(n + 1)]
    out = []
    for i in range(n):
        reason = rng.choice(REASONS)
        winner = rng.choice("ab")
        if reason == "in":  # landed inside the loser's half
            x = rng.uniform(0.5, 8.5) if winner == "b" else rng.uniform(9.5, 17.5)
            y = rng.uniform(0.3, 8.7)
        elif reason == "out":
            x, y = rng.choice([(rng.uniform(-2, 0), rng.uniform(0, 9)), (rng.uniform(0, 18), rng.uniform(9.2, 11))])
        else:
            x = y = None
        out.append({"idx": i, "start_s": round(edges[i] + 0.2, 2), "end_s": round(edges[i + 1] - 0.2, 2),
                    "winner": winner, "reason": reason, "confidence": round(rng.uniform(0.4, 0.98), 2),
                    "landing_x": x, "landing_y": y, "source": "demo"})
    return out


def _flight(a, b, T: float, start_frame: int, fps: float) -> dict:
    """The ballistic flight from a to b in T seconds, in the trajectory stage's flights.json shape."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    v0 = (b - a - 0.5 * G * T ** 2) / T
    end = start_frame + max(1, int(round(T * fps)))
    fit = FlightFit(start_frame, end, a, v0, fps, 0.0, 0.0)
    return {"start_frame": start_frame, "end_frame": end, "p0": a.tolist(), "v0": v0.tolist(), "fit_px": None,
            "depth_sd_m": 0.0, "quality": "ok", "reasons": [], "derived": fit.derived()}


# realistic flight times (s): serve, pass, set, attack (the attack slows to a tip when it must)
DEMO_TIMES = (1.2, 1.0, 0.9, 0.5)
NET_CLEARANCE_M = 2.6  # demo flights cross the net above this (net top 2.43 m)


def _attack_time(a, b) -> float:
    """Shortest attack time whose path crosses the net above NET_CLEARANCE_M: a spike for a deep landing,
    a slower tip over the net for a landing close to it."""
    for T in np.arange(0.5, 1.5, 0.05):
        v0 = (np.asarray(b) - np.asarray(a) - 0.5 * G * T ** 2) / T
        t = (9.0 - a[0]) / v0[0]
        if a[2] + v0[2] * t - 4.905 * t * t >= NET_CLEARANCE_M:
            return float(T)
    return 1.5


def demo_flights(rallies: list[dict], fps: float) -> list[dict]:
    """Placeholder flights for demo rallies: serve, pass, set and attack, the attack landing at the rally's
    landing point (or in the loser's half). Flights take realistic times; a rally too short for all four
    keeps the last ones (a 1.5 s rally shows only the attack). Deterministic per rally; labelled demo."""
    out = []
    for r in rallies:
        rng = random.Random(r["idx"])
        winner = r.get("winner") or rng.choice("ab")
        if r.get("landing_x") is not None:
            land = (r["landing_x"], r["landing_y"])
        else:  # in the half of the team that lost the rally
            land = (rng.uniform(1, 8), rng.uniform(1, 8)) if winner == "b" else (rng.uniform(10, 17), rng.uniform(1, 8))
        attack_b = land[0] < 9.0                      # the attack comes from the other half
        net_x = 10.2 if attack_b else 7.8             # setter and attacker near the net
        rx = rng.uniform(13, 16) if attack_b else rng.uniform(2, 5)  # receiver in the attacking half
        sx = -1.0 if attack_b else 19.0               # server behind the other end line
        points = [(sx, rng.uniform(1, 8), 3.0), (rx, rng.uniform(1.5, 7.5), 0.8),
                  (net_x, rng.uniform(4, 6), 2.6), (net_x, rng.choice([1.0, 8.0]), 3.2),
                  (land[0], land[1], BALL_RADIUS)]
        times = (*DEMO_TIMES[:3], _attack_time(points[3], points[4]))
        budget = 0.95 * (r["end_s"] - r["start_s"])
        k = 4
        while k > 0 and sum(times[4 - k:]) > budget:
            k -= 1
        if k == 0:
            continue
        frame = int(round(r["start_s"] * fps))
        for i in range(4 - k, 4):
            f = _flight(points[i], points[i + 1], times[i], frame, fps)
            out.append(f)
            frame = f["end_frame"]
    return out


def main():
    from main import register  # registering also queues the analysis job

    db = Database(DB_PATH)
    known = {v["path"] for v in db.list_videos()}
    rng = random.Random(0)
    for clip in sorted(VIDEOS.glob("*.mp4")):
        if str(clip.resolve()) in known:
            print(f"{clip.name}: already imported")
            continue
        v = register(clip.stem, clip.resolve())
        db.replace_rallies(v.id, demo_rallies(v.frames / v.fps, rng))
        print(f"{clip.name}: imported as {v.id}")


if __name__ == "__main__":
    main()
