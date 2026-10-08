"""Import the evaluation clips and give them placeholder rallies for UI work.

Ball tracking on these clips is real (the worker runs the pipeline). Rally segmentation and
scoring do not exist yet, so the rallies here are synthetic, stored with source='demo', and the
UI labels them as demo data.

Usage: python backend/demo.py
"""
import random

from vball.paths import VIDEOS

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
