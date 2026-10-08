"""Player tracking accuracy on labelled volleyball sequences (SportsMOT volleyball, MOT format).

Runs `vball.players.track_frames` on each sequence and scores it with TrackEval (the reference
HOTA implementation, unmodified in external/TrackEval): HOTA, IDF1, MOTA, detection recall and
precision, plus CPU time per detected frame. Results are labelled data, never proxies.

Usage:
  .venv/bin/python scripts/eval_player_tracking.py --model yolo26n.pt --imgsz 960 --tracker botsort.yaml --det-fps 10
  .venv/bin/python scripts/eval_player_tracking.py --gt-as-tracker      # sanity check: must score 1.0
  options: --seqs N (first N volleyball sequences), --max-frames N (per sequence, for quick runs)
"""
import argparse
import configparser
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vball.paths import DATASETS, EXTERNAL, OUTPUTS  # noqa: E402
from vball.players import TrackerConfig, track_frames, ultralytics_step  # noqa: E402

SPORTSMOT = DATASETS / "sportsmot"
GT_ROOT = SPORTSMOT / "val"
RESULTS = OUTPUTS / "player_tracking"


def volleyball_val_seqs() -> list[str]:
    vb = set((SPORTSMOT / "volleyball.txt").read_text().split())
    return [s for s in (SPORTSMOT / "val.txt").read_text().split() if s in vb]


def seq_info(seq: str) -> tuple[float, int]:
    ini = configparser.ConfigParser()
    ini.read(GT_ROOT / seq / "seqinfo.ini")
    return float(ini["Sequence"]["frameRate"]), int(ini["Sequence"]["seqLength"])


def write_mot(df: pd.DataFrame, path: Path) -> None:
    """MOTChallenge rows: frame (1-based), id (>= 1), left, top, width, height, conf, -1, -1, -1."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame({
        "frame": df["frame"] + 1, "id": df["track_id"] + 1 - df["track_id"].min() if len(df) else [],
        "x": df["x1"], "y": df["y1"], "w": df["x2"] - df["x1"], "h": df["y2"] - df["y1"], "conf": df["conf"],
    })
    out["a"] = out["b"] = out["c"] = -1
    out.to_csv(path, header=False, index=False, float_format="%.2f")


def run_tracker(seqs: list[str], cfg: TrackerConfig, label: str, max_frames: int | None) -> dict[str, float]:
    """Track every sequence; returns CPU ms per detected frame for each."""
    ms = {}
    for seq in seqs:
        fps, n = seq_info(seq)
        files = sorted((GT_ROOT / seq / "img1").glob("*.jpg"))[: max_frames or None]
        step = ultralytics_step(cfg)  # fresh tracker state per sequence
        times = []

        def timed(image):
            t0 = time.perf_counter()
            rows = step(image)
            times.append(time.perf_counter() - t0)
            return rows

        df = track_frames((cv2.imread(str(f)) for f in files), src_fps=fps, cfg=cfg, step=timed)
        write_mot(df, RESULTS / label / "data" / f"{seq}.txt")
        ms[seq] = 1000 * float(np.median(times[1:] or times))  # first call includes model warm-up
        print(f"  {seq}: {len(files)} frames, {len(times)} detected, {ms[seq]:.0f} ms/detected frame", flush=True)
    return ms


def gt_as_tracker(seqs: list[str], label: str, max_frames: int | None) -> None:
    for seq in seqs:
        gt = pd.read_csv(GT_ROOT / seq / "gt" / "gt.txt", header=None)
        if max_frames:
            gt = gt[gt[0] <= max_frames]
        out = gt.iloc[:, :6].copy()
        out[6] = 1.0
        out[7] = out[8] = out[9] = -1
        path = RESULTS / label / "data" / f"{seq}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(path, header=False, index=False)


def evaluate(seqs: list[str], label: str, max_frames: int | None) -> pd.DataFrame:
    # TrackEval still uses numpy aliases removed in numpy 1.24; restore them for it only.
    for name, typ in (("float", float), ("int", int), ("bool", bool)):
        if not hasattr(np, name):
            setattr(np, name, typ)
    sys.path.insert(0, str(EXTERNAL / "TrackEval"))
    import trackeval

    gt_folder = RESULTS / "_gt"  # GT copies, cut to max_frames when given
    for seq in seqs:
        dst = gt_folder / seq
        (dst / "gt").mkdir(parents=True, exist_ok=True)
        gt = pd.read_csv(GT_ROOT / seq / "gt" / "gt.txt", header=None)
        ini = (GT_ROOT / seq / "seqinfo.ini").read_text()
        if max_frames:
            gt = gt[gt[0] <= max_frames]
            n = min(max_frames, seq_info(seq)[1])
            ini = "\n".join(f"seqLength={n}" if line.startswith("seqLength") else line for line in ini.splitlines())
        gt.to_csv(dst / "gt" / "gt.txt", header=False, index=False)
        (dst / "seqinfo.ini").write_text(ini)
    seqmap = gt_folder / "seqmap.txt"
    seqmap.write_text("name\n" + "\n".join(seqs) + "\n")  # TrackEval skips the first line as a header

    eval_cfg = trackeval.Evaluator.get_default_eval_config()
    eval_cfg.update({"PRINT_RESULTS": False, "PRINT_CONFIG": False, "OUTPUT_SUMMARY": False,
                     "OUTPUT_DETAILED": False, "PLOT_CURVES": False, "USE_PARALLEL": False})
    ds_cfg = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    ds_cfg.update({"GT_FOLDER": str(gt_folder), "TRACKERS_FOLDER": str(RESULTS), "TRACKERS_TO_EVAL": [label],
                   "SEQMAP_FILE": str(seqmap), "SKIP_SPLIT_FOL": True, "DO_PREPROC": False,
                   "PRINT_CONFIG": False, "TRACKER_SUB_FOLDER": "data", "OUTPUT_SUB_FOLDER": "eval"})
    metrics = [trackeval.metrics.HOTA(), trackeval.metrics.CLEAR(), trackeval.metrics.Identity()]
    res, _ = trackeval.Evaluator(eval_cfg).evaluate([trackeval.datasets.MotChallenge2DBox(ds_cfg)], metrics)
    per_seq = res["MotChallenge2DBox"][label]
    rows = []
    for seq, r in per_seq.items():
        p = r["pedestrian"]
        rows.append({"seq": seq, "HOTA": float(np.mean(p["HOTA"]["HOTA"])), "IDF1": p["Identity"]["IDF1"],
                     "MOTA": p["CLEAR"]["MOTA"], "recall": p["CLEAR"]["CLR_Re"], "precision": p["CLEAR"]["CLR_Pr"],
                     "IDSW": p["CLEAR"]["IDSW"]})
    return pd.DataFrame(rows).set_index("seq")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="yolo26n.pt")
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--tracker", default="botsort.yaml")
    ap.add_argument("--det-fps", type=float, default=10.0)
    ap.add_argument("--seqs", type=int, default=None, help="only the first N volleyball sequences")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--gt-as-tracker", action="store_true")
    args = ap.parse_args()

    seqs = volleyball_val_seqs()[: args.seqs]
    if args.gt_as_tracker:
        label, ms = "ground_truth", {}
        gt_as_tracker(seqs, label, args.max_frames)
    else:
        cfg = TrackerConfig(args.model, args.imgsz, args.tracker, args.det_fps)
        label = cfg.label() + (f"_first{args.max_frames}" if args.max_frames else "")
        print(f"{label} on {len(seqs)} volleyball validation sequences")
        ms = run_tracker(seqs, cfg, label, args.max_frames)
    table = evaluate(seqs, label, args.max_frames)
    if ms:
        table["ms_per_detected_frame"] = pd.Series(ms)
        table.loc["COMBINED_SEQ", "ms_per_detected_frame"] = float(np.median(list(ms.values())))
    # COMBINED_SEQ is TrackEval's own combination over all sequences (metrics recomputed from the
    # pooled matches); averaging per-sequence HOTA or IDF1 would be wrong.
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()
