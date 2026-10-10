"""3D trajectory fit on synthetic rallies through a known broadcast-like camera.

A serve -> receive -> set -> attack rally (1080p, 50 fps) is rendered with Gaussian detection noise
and reconstructed with the true flight boundaries and the true camera, so the numbers isolate the
ballistic fit. Reports per flight type: median 3D error, mid-flight error over the reported depth
standard deviation, and the share flagged low quality. Also checks segmentation against the true touches.

  .venv/bin/python scripts/eval_trajectory_synthetic.py [--seeds 20] [--noise 2]
  .venv/bin/python scripts/eval_trajectory_synthetic.py --ablation [--miss 0.3] [--false 0.12]

--ablation (change constrain-3d-flights): detections corrupted as on the evaluation clips (missed in bursts, false
points, noise), true flight boundaries, and four fit settings: no constraints, bounds, + robust refit,
+ player anchors (a player near each touch, ~0.3 m from the touch's ground point).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_trajectory import CAM, DURATIONS, FPS, SIZE, TOUCHES, true_flights  # noqa: E402  same scenario as the tests

from vball.trajectory import FlightConfig, fit, segment  # noqa: E402
from vball.trajectory.synthetic import corrupt, render, touch_players  # noqa: E402

NAMES = ["serve", "receive", "set", "attack"]


ABLATION = {"none": FlightConfig(robust=False, bounded=False), "bounds": FlightConfig(robust=False),
            "+ robust": FlightConfig(), "+ anchors": FlightConfig()}


def ablation(seeds: int, miss: float, false: float, noise: float) -> None:
    errs = {c: {n: [] for n in NAMES} for c in ABLATION}
    dropped, anchored, ends = 0, 0, 0
    for seed in range(seeds):
        r = render(CAM, TOUCHES, DURATIONS, FPS)
        uv = corrupt(r.uv, SIZE, miss=miss, false=false, noise_px=noise, seed=seed)
        players = touch_players(TOUCHES, seed=seed)
        for n, fl, pa, pb in zip(NAMES, true_flights(r), players, players[1:]):
            frames = np.arange(fl.start, fl.end + 1)
            for c, cfg in ABLATION.items():
                pat = None
                if c == "+ anchors":
                    pat = {"start": None if pa is None else [pa], "end": None if pb is None else [pb]}
                try:
                    f = fit(CAM, uv, fl, FPS, cfg, players_at=pat)
                except ValueError:
                    errs[c][n].append(np.nan)
                    continue
                errs[c][n].append(np.median(np.linalg.norm(f.at(frames) - r.positions[frames], axis=1)))
                if c == "+ anchors":
                    dropped += f.dropped
                    anchored += len(f.anchors)
                    ends += (pa is not None) + (pb is not None)
    print(f"{seeds} seeds, {miss:.0%} missed (bursts), {false:.0%} false, {noise} px noise; true flight boundaries")
    print("median 3D error (m)  " + "".join(f"{n:>10s}" for n in NAMES))
    for c in ABLATION:
        print(f"{c:20s} " + "".join(f"{np.nanmedian(errs[c][n]):10.2f}" for n in NAMES))
    print(f"detections dropped by the robust refit: {dropped}; touches anchored: {anchored} of {ends} with a player")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--noise", type=float, default=2.0)
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--miss", type=float, default=0.3)
    ap.add_argument("--false", type=float, default=0.12)
    args = ap.parse_args()
    if args.ablation:
        ablation(args.seeds, args.miss, args.false, args.noise)
        return

    rows = {n: [] for n in NAMES}
    seg_ok = 0
    for seed in range(args.seeds):
        r = render(CAM, TOUCHES, DURATIONS, FPS, noise_px=args.noise, seed=seed)
        found = [(f.start, f.end) for f in segment(r.uv)]
        truth = list(zip(r.touches, r.touches[1:]))
        seg_ok += len(found) == len(truth) and all(abs(a - c) <= 2 and abs(b - d) <= 2
                                                   for (a, b), (c, d) in zip(found, truth))
        for n, fl in zip(NAMES, true_flights(r)):
            f = fit(CAM, r.uv, fl, FPS)
            frames = np.arange(fl.start, fl.end + 1)
            err = np.linalg.norm(f.at(frames) - r.positions[frames], axis=1)
            mid = len(frames) // 2
            rows[n].append((np.median(err), err[mid] / f.depth_sd_m, f.depth_sd_m, f.quality == "low",
                            len(frames) / FPS))

    print(f"{args.seeds} seeds, {args.noise} px noise, camera f = {CAM.focal:.0f} px at "
          f"{np.round(CAM.position, 1).tolist()} m, {FPS:.0f} fps")
    print(f"segmentation: all touches within 2 frames in {seg_ok}/{args.seeds} rallies")
    print("flight    duration_s  median_err_m  p90_err_m  depth_sd_m  max_err/sd  low_quality")
    for n, s in rows.items():
        s = np.array(s, float)
        print(f"{n:9s} {s[0, 4]:10.2f} {np.median(s[:, 0]):13.3f} {np.quantile(s[:, 0], 0.9):10.3f} "
              f"{np.median(s[:, 2]):11.2f} {s[:, 1].max():11.2f} {int(s[:, 3].sum()):6d}/{args.seeds}")


if __name__ == "__main__":
    main()
