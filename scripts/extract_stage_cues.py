"""Rally cues for fixed-camera matches from the pipeline's own stages (change label-rallies-from-score, task 2.1).

For every full match in a folder: the pipeline's decode (shots, camera motion), court (line evidence for
still shots) and ball (VballNet) stages run into results/<video stem>/, people are detected twice a second with the
pipeline's general person detector (the player-only one sees too few people in end-line views), and
`vball.rally_cues.stage_cues` turns them into cues for every camera shot whose court is ok. Using the stages
themselves keeps the training cues identical to what the rallies stage computes.

  .venv/bin/python scripts/extract_stage_cues.py              # data/datasets/watchdog/videos -> .../cues/<stem>.csv
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from vball import pipeline, players
from vball.paths import DATASETS
from vball.rally_cues import shot_cues


def match_cues(video: Path, out: Path) -> pd.DataFrame:
    out.mkdir(parents=True, exist_ok=True)
    prev = {}
    for name, fn in (("decode", pipeline.decode.run), ("court", pipeline.court.run), ("ball", pipeline.ball.run)):
        res = pipeline.load_stage(out, name)
        if res is None or res.get("version") != pipeline.VERSIONS[name]:
            res = {"version": pipeline.VERSIONS[name], **fn(video, out, prev, lambda f: None)}
            pipeline.stage_file(out, name).write_text(json.dumps(res))
        prev[name] = res
    meta = prev["decode"]
    fps, n, size = meta["fps"], meta["frames"], (meta["width"], meta["height"])
    people_csv = out / "people.csv.gz"
    if people_csv.exists():
        people = pd.read_csv(people_csv)
    else:
        people = pipeline.models.people_boxes(video, n, players.sample_every(fps, pipeline.config.PEOPLE_FPS))
        people.to_csv(people_csv, index=False)  # full precision: a rerun reads exactly what the first run used
    return shot_cues(prev["court"], pd.read_csv(out / "ball.csv"), people, fps, size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=Path, default=DATASETS / "watchdog" / "videos")
    ap.add_argument("--results", type=Path, default=DATASETS / "watchdog" / "results")
    ap.add_argument("--out", type=Path, default=DATASETS / "watchdog" / "cues")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for video in sorted(args.videos.glob("*.mp4")):
        dst = args.out / f"{video.stem}.csv"
        if dst.exists():
            continue
        cues = match_cues(video, args.results / video.stem)
        cues.to_csv(dst, index=False)
        print(
            f"{video.stem}: {len(cues)} samples over {cues['shot'].nunique() if len(cues) else 0} ok shots", flush=True
        )


if __name__ == "__main__":
    main()
