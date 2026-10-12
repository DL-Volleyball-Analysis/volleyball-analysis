"""Ball detection measured against labelled frames: the Volleyball dataset with ball annotations.

Data: the Volleyball dataset (Ibrahim et al., CVPR 2016; 55 broadcast matches, clips of 41 frames at 1280 x 720)
with the ball position annotated in every frame by Perez et al. (Pattern Recognition 2022). The official test
split (16 matches, 1,337 clips) is used; nothing here was tuned on it.

Methods: each detector of vball.ball_detect (v4c, v4c-tiles, ravel011, ravel012) alone (its most confident
candidate per frame) and with vball.ball_track (`<detector>+track`: fixed-object check, linking, gap filling).
A frame counts as a true positive when the predicted ball is within tau pixels of the label; a prediction
farther away is both a false positive and a miss (vball.metrics.accuracy). Reported for tau = 4 px (as WASB,
BMVC 2023) and 10 px.

Second dataset (`--dataset orel`): the held-out gym matches of volleyball-orel.ru (scripts/build_ball_clips.py,
OREL_TEST: a backline and a side view), labels in original pixels.

  python scripts/eval_ball_detection.py --videos <dir with <match>/<clip>/<frame>.jpg> \
      --ann <volleyball_ball_annotation dir> [--max-clips N] [--detectors v4c ravel012] [--no-track]
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball import ball_detect
from vball.ball_track import TrackConfig, track
from vball.metrics import accuracy
from vball.paths import OUTPUTS

TEST_MATCHES = [4, 5, 9, 11, 14, 20, 21, 25, 29, 34, 35, 37, 43, 44, 45, 47]  # official split (deep-activity-rec)
TAUS = (4.0, 10.0)


def labels_frame(xy: np.ndarray, vis: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({"frame": np.arange(len(xy)), "visible": vis.astype(int), "x": xy[:, 0], "y": xy[:, 1]})


def orel_clips(root: Path):
    """(match, clip, frame loader, labels) for the held-out orel gym matches."""
    from vball.datasets import ball_clips as bbc
    for match, clip, video, xy, vis in bbc.orel_clips(root):
        if match in bbc.OREL_TEST:
            yield match, clip, (lambda v=video: list(bbc.read_video(v))), labels_frame(xy, vis)


def clips(videos: Path, ann: Path, matches: list[int]):
    """(match, clip, frame loader, labels DataFrame) for every annotated clip of the given matches."""
    for m in matches:
        for a in sorted((ann / str(m)).glob("*.txt"), key=lambda p: int(p.stem)):
            d = videos / str(m) / a.stem
            frames = sorted(d.glob("*.jpg"), key=lambda p: int(p.stem))
            xy = np.loadtxt(a, ndmin=2)
            if len(frames) != len(xy):
                continue
            vis = ~((xy[:, 0] == 0) & (xy[:, 1] == 0))
            yield m, a.stem, (lambda fs=frames: [cv2.imread(str(f)) for f in fs]), labels_frame(xy, vis)


def best_per_frame(cands) -> pd.DataFrame:
    rows = []
    for i, cs in enumerate(cands):
        c = max(cs, key=lambda c: c.score) if cs else None
        rows.append((i, int(c is not None), c.x if c else np.nan, c.y if c else np.nan))
    return pd.DataFrame(rows, columns=["frame", "visible", "x", "y"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["volleyball", "orel"], default="volleyball")
    ap.add_argument("--videos", help="Volleyball dataset frames")
    ap.add_argument("--ann", help="Volleyball dataset ball annotations")
    ap.add_argument("--orel", help="volleyball-orel.ru data root")
    ap.add_argument("--detectors", nargs="+", default=ball_detect.DETECTORS, choices=ball_detect.DETECTORS)
    ap.add_argument("--no-track", action="store_true", help="only the detectors alone")
    ap.add_argument("--max-clips", type=int, default=None, help="evenly spaced subset of the test clips")
    ap.add_argument("--out", default=str(OUTPUTS / "ball" / "eval_volleyball"))
    ap.add_argument("--wasb-model", type=Path, default=None, help="another WASB ONNX (e.g. a fine-tuned run) for 'wasb'")
    args = ap.parse_args()
    if args.wasb_model is not None:
        ball_detect.BALL_MODELS["wasb"] = args.wasb_model

    dets = {d: ball_detect.load(d) for d in args.detectors}
    methods = [m for d in args.detectors for m in ([d] if args.no_track else [d, f"{d}+track"])]
    cfg = TrackConfig()
    if args.dataset == "volleyball":
        all_clips = list(clips(Path(args.videos), Path(args.ann), TEST_MATCHES))
    else:
        all_clips = list(orel_clips(Path(args.orel)))
    if args.max_clips and args.max_clips < len(all_clips):
        all_clips = [all_clips[i] for i in np.linspace(0, len(all_clips) - 1, args.max_clips).astype(int)]
    print(f"{len(all_clips)} test clips, {sum(len(c[3]) for c in all_clips)} frames")

    preds = {m: [] for m in methods}
    labels, secs = [], {m: 0.0 for m in methods}
    for n, (match, clip, load_frames, lab) in enumerate(all_clips):
        frames = load_frames()[:len(lab)]
        lab = lab.iloc[:len(frames)]
        key = {"match": match, "clip": clip}
        labels.append(lab.assign(**key))
        for d, det in dets.items():
            t0 = time.perf_counter()
            cands = det.candidates(frames)
            t_det = time.perf_counter() - t0
            secs[d] += t_det
            preds[d].append(best_per_frame(cands).assign(**key))
            if f"{d}+track" in preds:  # time = detection + tracking
                t1 = time.perf_counter()
                preds[f"{d}+track"].append(track(frames, cands, cfg)[["frame", "visible", "x", "y"]].assign(**key))
                secs[f"{d}+track"] += t_det + time.perf_counter() - t1
        if (n + 1) % 100 == 0:
            print(f"  {n + 1} clips", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gt = pd.concat(labels, ignore_index=True)
    gt["frame"] = np.arange(len(gt))  # one global frame index so clips do not collide in the merge
    n_frames = len(gt)
    results = {}
    print(f"\n{"method":16s} " + "  ".join(f"P/R/F1 @{t:.0f}px" for t in TAUS) + "   ms/frame")
    for m in methods:
        pr = pd.concat(preds[m], ignore_index=True)
        pr["frame"] = np.arange(len(pr))
        pr.to_csv(out / f"{m.replace('+', '_')}.csv.gz", index=False)
        res = {f"tau{int(t)}": accuracy(pr, gt, t) for t in TAUS}
        res["ms_per_frame"] = 1000 * secs[m] / n_frames
        results[m] = res
        cells = "  ".join(f"{r['precision']:.3f}/{r['recall']:.3f}/{r['f1']:.3f}" for r in (res[f"tau{int(t)}"] for t in TAUS))
        print(f"{m:16s} {cells}   {res['ms_per_frame']:.0f}")
    (out / "results.json").write_text(json.dumps({"clips": len(all_clips), "frames": n_frames,
                                                  "visible_share": float(gt["visible"].mean()), "methods": results}, indent=2))
    print(f"\nlabels: {gt['visible'].mean():.1%} of frames have a visible ball; results in {out}")


if __name__ == "__main__":
    main()
