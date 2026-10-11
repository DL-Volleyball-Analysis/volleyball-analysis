"""Ball training clips in one format from the public labelled sources (change train-ball-detector).

Every clip becomes a folder of consecutive frames letterboxed to the detector's input (512 x 288, the transform of
vball.ball_detect.Wasb) and `labels.csv` (frame, visible, x, y in input pixels; x = y = -1 when no ball). A manifest
lists source, match, clip, split, frames and visible frames.

Sources and splits (by match, so no match is in two splits):
  volleyball  the Volleyball dataset (Ibrahim et al., CVPR 2016) with Perez et al.'s ball positions: 41-frame clips;
              test = the official 16 test matches, train = all others (as WASB trains).
  orel        volleyball-orel.ru `data_20250711_2330` (indoor gyms, VballNet's author): videos with per-frame
              Frame,Visibility,X,Y CSVs; test = the matches in OREL_TEST (a backline and a side view), the beach match
              is left out, train = the rest. The author's own train/test folders split videos of the same
              matches, so they are merged and re-split here.

  python scripts/build_ball_clips.py --out <dir> [--volleyball-videos <dir> --volleyball-ann <dir>] [--orel <dir>]
"""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball.ball_detect import Wasb, letterbox, letterbox_image

VOLLEYBALL_TEST = [4, 5, 9, 11, 14, 20, 21, 25, 29, 34, 35, 37, 43, 44, 45, 47]
OREL_TEST = {"gtu_20250316_backline", "match3"}
OREL_SKIP = {"20250623_beach"}  # beach volleyball: not the indoor footage this detector is for
W, H = Wasb.W, Wasb.H


def to_input(xy: np.ndarray, visible: np.ndarray, width: int, height: int) -> np.ndarray:
    """Image positions -> input (512 x 288 letterbox) positions; -1 where there is no ball."""
    s, x0, y0 = letterbox(width, height, W, H)
    out = np.where(visible[:, None], xy * s + (x0, y0), -1.0)
    return np.round(out, 2)


def write_clip(folder: Path, frames, xy: np.ndarray, visible: np.ndarray) -> int:
    """frames: iterable of BGR images (all the same size); writes letterboxed JPEGs and labels.csv. Frames beyond the
    labels are ignored; returns the number written."""
    folder.mkdir(parents=True, exist_ok=True)
    n, size = 0, None
    for i, f in enumerate(frames):
        if i >= len(xy):
            break
        size = f.shape[1], f.shape[0]
        cv2.imwrite(str(folder / f"{i:05d}.jpg"), letterbox_image(f, W, H), [cv2.IMWRITE_JPEG_QUALITY, 92])
        n += 1
    if size is None:
        return 0
    p = to_input(xy[:n], visible[:n], *size)
    with (folder / "labels.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "visible", "x", "y"])
        w.writerows((i, int(v), x, y) for i, (v, (x, y)) in enumerate(zip(visible[:n], p)))
    return n


def volleyball_clips(videos: Path, ann: Path):
    """(match, clip, frame paths, xy, visible) for every annotated clip."""
    for match_dir in sorted(ann.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else -1):
        if not match_dir.name.isdigit():
            continue
        for a in sorted(match_dir.glob("*.txt")):
            frames = sorted((videos / match_dir.name / a.stem).glob("*.jpg"), key=lambda p: int(p.stem))
            xy = np.loadtxt(a, ndmin=2)
            if len(frames) != len(xy):
                continue
            yield int(match_dir.name), a.stem, frames, xy, ~((xy[:, 0] == 0) & (xy[:, 1] == 0))


def orel_clips(root: Path):
    """(match, clip, video path, xy, visible) for every video with a ball CSV, both of the author's folders."""
    for csv_path in sorted(root.glob("data/*/*/csv/*_ball.csv")):
        match = csv_path.parts[-3]
        if match in OREL_SKIP:
            continue
        stem = csv_path.name[: -len("_ball.csv")]
        video = csv_path.parent.parent / "video" / f"{stem}.mp4"
        if not video.exists():
            continue
        d = pd.read_csv(csv_path).sort_values("Frame")
        visible = (d["Visibility"] > 0).to_numpy()
        yield match, stem, video, d[["X", "Y"]].to_numpy(float), visible


def read_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()


def build(out: Path, volleyball: tuple[Path, Path] | None = None, orel: Path | None = None) -> pd.DataFrame:
    rows = []
    if volleyball:
        for match, clip, paths, xy, vis in volleyball_clips(*volleyball):
            split = "test" if match in VOLLEYBALL_TEST else "train"
            name = f"volleyball/{match}_{clip}"
            n = write_clip(out / name, (cv2.imread(str(p)) for p in paths), xy, vis)
            rows.append(("volleyball", str(match), clip, split, name, n, int(vis[:n].sum())))
    if orel:
        for match, clip, video, xy, vis in orel_clips(orel):
            split = "test" if match in OREL_TEST else "train"
            name = f"orel/{match}__{clip}"
            n = write_clip(out / name, read_video(video), xy, vis)
            rows.append(("orel", match, clip, split, name, n, int(vis[:n].sum())))
    m = pd.DataFrame(rows, columns=["source", "match", "clip", "split", "folder", "frames", "visible"])
    out.mkdir(parents=True, exist_ok=True)
    m.to_csv(out / "manifest.csv", index=False)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--volleyball-videos")
    ap.add_argument("--volleyball-ann")
    ap.add_argument("--orel")
    args = ap.parse_args()
    vb = (Path(args.volleyball_videos), Path(args.volleyball_ann)) if args.volleyball_videos else None
    m = build(Path(args.out), vb, Path(args.orel) if args.orel else None)
    print(m.groupby(["source", "split"])[["frames", "visible"]].sum().assign(clips=m.groupby(["source", "split"]).size()))


if __name__ == "__main__":
    main()
