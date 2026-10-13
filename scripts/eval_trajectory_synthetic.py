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

--stress: the same corrupted detections under harder, more realistic conditions, robust fit with and without anchors:
twelve players on court in a match formation (the anchor may pick the wrong one), the touching player's position off
by 0.3 / 0.6 / 1.0 m, flights cut by the system's own segmentation instead of the true touches, and a camera that is
slightly off (focal length +3%, position 0.3 m). Also counts anchors on the wrong player.
"""

import argparse

import numpy as np

from vball.trajectory import FlightConfig, fit, segment
from vball.trajectory.synthetic import CAM, DURATIONS, FPS, SIZE, TOUCHES, corrupt, render, touch_players, true_flights

NAMES = ["serve", "receive", "set", "attack"]


ABLATION = {
    "none": FlightConfig(robust=False, bounded=False),
    "bounds": FlightConfig(robust=False),
    "+ robust": FlightConfig(),
    "+ anchors": FlightConfig(),
}


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


# a match formation (court metres, side A is x < 9): six players per side; side A blocks at the net during the attack
FORMATION_A = [[3.0, 1.5], [3.0, 4.5], [3.0, 7.5], [7.6, 1.5], [7.6, 4.5], [7.6, 7.5]]
FORMATION_B = [[15.0, 1.5], [15.0, 4.5], [15.0, 7.5], [10.6, 1.5], [10.6, 4.5], [10.6, 7.5]]
BLOCK_A = [[8.4, 1.2], [8.4, 2.4]]  # two blockers facing the attack at y = 1


def court_players(touch_xy, k: int, rng, jitter_m: float, spread_m: float = 0.5) -> np.ndarray:
    """Twelve court positions at touch k: the touching player (true ground point plus jitter_m) and eleven others in
    the formation (each off by spread_m), the formation slot nearest the touching player left out."""
    slots = np.array(FORMATION_A + FORMATION_B, float)
    if k == 3:  # the attack: side A's front row moves to block
        slots[3:5] = BLOCK_A
    toucher = np.asarray(touch_xy, float) + rng.normal(0, jitter_m, 2)
    others = np.delete(slots, int(np.argmin(np.linalg.norm(slots - touch_xy, axis=1))), axis=0)
    return np.vstack([toucher, others + rng.normal(0, spread_m, others.shape)])


def matched_flights(found, truth, min_overlap: float = 0.5):
    """For each true flight, the found flight overlapping it most (by frames), or None below min_overlap."""
    out = []
    for t in truth:
        best, share = None, 0.0
        for f in found:
            inter = min(f.end, t.end) - max(f.start, t.start) + 1
            if inter > 0 and inter / (t.end - t.start + 1) > share:
                best, share = f, inter / (t.end - t.start + 1)
        out.append(best if share >= min_overlap else None)
    return out


def stress(seeds: int, miss: float, false: float, noise: float) -> None:
    from vball.calibration import look_at

    off_cam = look_at(np.asarray(CAM.position) + [0.3, 0.0, 0.0], [9.0, 4.5, 0.5], CAM.focal * 1.03, SIZE)
    conditions = {
        "touching player only, 0.3 m": dict(crowd=False, jitter=0.3),
        "12 players, 0.3 m": dict(crowd=True, jitter=0.3),
        "12 players, 0.6 m": dict(crowd=True, jitter=0.6),
        "12 players, 1.0 m": dict(crowd=True, jitter=1.0),
        "12 players, 0.6 m, own segmentation": dict(crowd=True, jitter=0.6, segment=True),
        "12 players, 0.6 m, camera off": dict(crowd=True, jitter=0.6, camera=off_cam),
    }
    margins = {"no anchors": None, "margin 0 (old)": 0.0, "margin 0.5": 0.5, "margin 1.0 (default)": 1.0}
    print(
        f"{seeds} seeds, {miss:.0%} missed (bursts), {false:.0%} false, {noise} px noise; median 3D error (m) of the "
        "set / the attack; wrong anchors at the default margin"
    )
    print(f"{'condition':40s}" + "".join(f"{m:>22s}" for m in margins) + "   wrong   unmatched")
    for name, c in conditions.items():
        errs = {m: {n: [] for n in NAMES} for m in margins}
        wrong = total = unmatched = 0
        for seed in range(seeds):
            rng = np.random.default_rng(1000 + seed)
            r = render(CAM, TOUCHES, DURATIONS, FPS)
            uv = corrupt(r.uv, SIZE, miss=miss, false=false, noise_px=noise, seed=seed)
            truth = true_flights(r)
            flights = matched_flights(segment(uv), truth) if c.get("segment") else truth
            cam = c.get("camera", CAM)
            people = [
                None
                if k == len(TOUCHES) - 1
                else (
                    court_players(np.asarray(t)[:2], k, rng, c["jitter"])
                    if c["crowd"]
                    else np.asarray(t, float)[:2][None] + rng.normal(0, c["jitter"], (1, 2))
                )
                for k, t in enumerate(TOUCHES)
            ]
            for k, (n, fl, tf) in enumerate(zip(NAMES, flights, truth)):
                frames = np.arange(tf.start, tf.end + 1)
                unmatched += fl is None
                for m, margin in margins.items():
                    if fl is None:
                        errs[m][n].append(np.nan)
                        continue
                    pat = None if margin is None else {"start": people[k], "end": people[k + 1]}
                    try:
                        f = fit(cam, uv, fl, FPS, FlightConfig(anchor_margin_m=margin or 0.0), players_at=pat)
                    except ValueError:
                        errs[m][n].append(np.nan)
                        continue
                    errs[m][n].append(np.median(np.linalg.norm(f.at(frames) - r.positions[frames], axis=1)))
                    if margin == 1.0:
                        for end, idx in (("start", k), ("end", k + 1)):
                            if end in f.anchors and people[idx] is not None:
                                total += 1
                                wrong += bool(np.linalg.norm(np.asarray(f.anchor_xy[end]) - people[idx][0]) > 1e-9)
        cells = "".join(
            f"{np.nanmedian(errs[m]['set']):12.2f} /{np.nanmedian(errs[m]['attack']):6.2f}  " for m in margins
        )
        print(f"{name:40s}{cells}  {wrong:3d}/{total:<4d}  {unmatched:4d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--noise", type=float, default=2.0)
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--stress", action="store_true", help="anchors under crowded, noisy and imperfect conditions")
    ap.add_argument("--miss", type=float, default=0.3)
    ap.add_argument("--false", type=float, default=0.12)
    args = ap.parse_args()
    if args.ablation:
        ablation(args.seeds, args.miss, args.false, args.noise)
        return
    if args.stress:
        stress(args.seeds, args.miss, args.false, args.noise)
        return

    rows = {n: [] for n in NAMES}
    seg_ok = 0
    for seed in range(args.seeds):
        r = render(CAM, TOUCHES, DURATIONS, FPS, noise_px=args.noise, seed=seed)
        found = [(f.start, f.end) for f in segment(r.uv)]
        truth = list(zip(r.touches, r.touches[1:]))
        seg_ok += len(found) == len(truth) and all(
            abs(a - c) <= 2 and abs(b - d) <= 2 for (a, b), (c, d) in zip(found, truth)
        )
        for n, fl in zip(NAMES, true_flights(r)):
            f = fit(CAM, r.uv, fl, FPS)
            frames = np.arange(fl.start, fl.end + 1)
            err = np.linalg.norm(f.at(frames) - r.positions[frames], axis=1)
            mid = len(frames) // 2
            rows[n].append(
                (np.median(err), err[mid] / f.depth_sd_m, f.depth_sd_m, f.quality == "low", len(frames) / FPS)
            )

    print(
        f"{args.seeds} seeds, {args.noise} px noise, camera f = {CAM.focal:.0f} px at "
        f"{np.round(CAM.position, 1).tolist()} m, {FPS:.0f} fps"
    )
    print(f"segmentation: all touches within 2 frames in {seg_ok}/{args.seeds} rallies")
    print("flight    duration_s  median_err_m  p90_err_m  depth_sd_m  max_err/sd  low_quality")
    for n, s in rows.items():
        s = np.array(s, float)
        print(
            f"{n:9s} {s[0, 4]:10.2f} {np.median(s[:, 0]):13.3f} {np.quantile(s[:, 0], 0.9):10.3f} "
            f"{np.median(s[:, 2]):11.2f} {s[:, 1].max():11.2f} {int(s[:, 3].sum()):6d}/{args.seeds}"
        )


if __name__ == "__main__":
    main()
