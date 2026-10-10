"""Build a player-only detection set (YOLO format, one class) from SportsMOT volleyball training sequences.

SportsMOT labels only the players on court; referees, coaches, the bench and spectators are distractors by design,
so a detector fine-tuned on these labels learns to leave them out (change filter-on-court-players). Every
`--every`-th frame is kept (consecutive frames are near duplicates). The 15 training sequences come from 5 match
videos; the validation split holds out whole videos. SportsMOT's own volleyball validation sequences are never
used here: they stay for the tracking evaluation (scripts/eval_player_tracking.py).

Licence: SportsMOT is CC BY-NC 4.0 (research use, not redistributed). Runs where the data is, e.g. on Kaggle:

  python scripts/build_sportsmot_detection.py --src <dir with train/<seq>/...> --out <dir> [--every 3]
"""
import argparse
import configparser
import shutil
from pathlib import Path

# SportsMOT train.txt ∩ volleyball.txt (dataset/splits_txt in the SportsMOT release)
VOLLEYBALL_TRAIN = [
    "v_1LwtoLPw2TU_c006", "v_1LwtoLPw2TU_c012", "v_1LwtoLPw2TU_c014", "v_1LwtoLPw2TU_c016",
    "v_ApPxnw_Jffg_c001", "v_ApPxnw_Jffg_c002", "v_ApPxnw_Jffg_c009", "v_ApPxnw_Jffg_c015", "v_ApPxnw_Jffg_c016",
    "v_CW0mQbgYIF4_c004", "v_CW0mQbgYIF4_c005", "v_CW0mQbgYIF4_c006",
    "v_dChHNGIfm4Y_c003", "v_Dk3EpDDa3o0_c002", "v_Dk3EpDDa3o0_c007",
]
VALID_VIDEOS = {"v_Dk3EpDDa3o0"}  # whole match video held out for model selection


def video_of(seq: str) -> str:
    return seq.rsplit("_c", 1)[0]


def mot_to_yolo(rows: list[tuple[float, float, float, float]], width: int, height: int) -> str:
    """MOT boxes (x, y, w, h in pixels) -> YOLO label lines (class 0, normalised centre and size), clipped to the
    image; boxes left with no area are dropped."""
    out = []
    for x, y, w, h in rows:
        x1, y1 = max(0.0, x), max(0.0, y)
        x2, y2 = min(float(width), x + w), min(float(height), y + h)
        if x2 <= x1 or y2 <= y1:
            continue
        out.append(f"0 {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} "
                   f"{(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}")
    return "\n".join(out) + ("\n" if out else "")


def read_gt(path: Path) -> dict[int, list[tuple[float, float, float, float]]]:
    boxes: dict[int, list] = {}
    for line in path.read_text().splitlines():
        p = [v.strip() for v in line.split(",")]
        if len(p) >= 6:
            boxes.setdefault(int(float(p[0])), []).append(tuple(float(v) for v in p[2:6]))
    return boxes


def build(src: Path, out: Path, seqs: list[str], every: int = 3) -> dict[str, int]:
    shutil.rmtree(out, ignore_errors=True)
    counts = {"train": 0, "valid": 0}
    for seq in seqs:
        d = src / seq
        if not d.exists():
            raise SystemExit(f"missing sequence {d}")
        info = configparser.ConfigParser()
        info.read(d / "seqinfo.ini")
        w, h = int(info["Sequence"]["imWidth"]), int(info["Sequence"]["imHeight"])
        ext = info["Sequence"].get("imExt", ".jpg")
        split = "valid" if video_of(seq) in VALID_VIDEOS else "train"
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        gt = read_gt(d / "gt" / "gt.txt")
        for frame in range(1, int(info["Sequence"]["seqLength"]) + 1, every):
            name = f"{seq}_{frame:06d}"
            shutil.copy2(d / "img1" / f"{frame:06d}{ext}", out / split / "images" / f"{name}{ext}")
            (out / split / "labels" / f"{name}.txt").write_text(mot_to_yolo(gt.get(frame, []), w, h))
            counts[split] += 1
    (out / "data.yaml").write_text(f"path: {out.resolve()}\ntrain: train/images\nval: valid/images\nnc: 1\nnames: [player]\n")
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder holding the sequences (SportsMOT train/)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=3)
    ap.add_argument("--seqs", nargs="*", default=VOLLEYBALL_TRAIN)
    args = ap.parse_args()
    print("images:", build(Path(args.src), Path(args.out), args.seqs, args.every))


if __name__ == "__main__":
    main()
