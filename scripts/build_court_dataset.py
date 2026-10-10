"""Build the court keypoint training set (v3b) for Colab and zip it to Google Drive.

- train / valid / test: volleyball-court-keypoints-k6y7r (14 points, image-based numbering).
- train also gets VNL broadcast clips one-three (every 2nd frame): their 4 labelled front-zone corners
  are completed to all 10 floor points by the floor homography (checked on k6y7r: 2.1 px median);
  points outside the image and the net points are left unlabelled (see the change's design.md).
- test_vnl: VNL clips four and five, completed the same way, never used for training. They share the
  broadcast with the training clips, so they are not unseen cameras.
- Boxes (v3b): every label's box is recomputed by one rule, the bounding box of its visible keypoints plus
  a 1% margin. v3 kept the k6y7r annotators' boxes (median 2.8x, p90 24x the floor-point extent) next to
  tight computed boxes for VNL (1.1x); a pose model regresses keypoints relative to its box, so the two
  conventions conflicted.

Usage: .venv/bin/python scripts/build_court_dataset.py [--no-drive]
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball.court_keypoints import FRONT_ZONE_IDS, K6Y7R_FLIP_IDX, complete_floor  # noqa: E402
from vball.paths import DATASETS  # noqa: E402

K6Y7R = DATASETS / "volleyball-court-keypoints-k6y7r-v1"
VNL = DATASETS / "volleyball_court_key_points_regression_dataset-v7"
OUT = DATASETS / "court_keypoints_v3b"
# The Google Drive desktop folder: VBALL_DRIVE_ACCOUNT if set, else the only Drive account found.
DRIVE_ACCOUNT_ENV = "VBALL_DRIVE_ACCOUNT"
DRIVE_RELPATH = "volleyball/datasets/court_keypoints_v3b.zip"  # Colab: /content/drive/MyDrive/<this>
VNL_TRAIN_CLIPS = ("clip_one", "clip_two", "clip_three")
VNL_TEST_CLIPS = ("clip_four", "clip_five")
VNL_TRAIN_EVERY = 2  # consecutive frames are near duplicates; keep VNL from outweighing k6y7r


def drive_root() -> Path:
    """'My Drive' is localised by the Drive app (e.g. 我的雲端硬碟), so find it instead of hard-coding."""
    if os.environ.get(DRIVE_ACCOUNT_ENV):
        accounts = [Path(os.environ[DRIVE_ACCOUNT_ENV])]
    else:
        accounts = sorted((Path.home() / "Library/CloudStorage").glob("GoogleDrive-*"))
    if len(accounts) != 1:
        raise SystemExit(f"set {DRIVE_ACCOUNT_ENV} to the Google Drive folder to use (found {len(accounts)})")
    for name in ("My Drive", "我的雲端硬碟"):
        if (accounts[0] / name).is_dir():
            return accounts[0] / name
    raise SystemExit(f"no 'My Drive' folder under {accounts[0]}")
K = len(K6Y7R_FLIP_IDX)


BOX_MARGIN = 0.01  # normalised


def keypoint_box(kp: np.ndarray) -> list[float]:
    """(cx, cy, w, h) normalised: bounding box of the visible keypoints plus a margin, inside the image."""
    vis = kp[kp[:, 2] > 0, :2]
    x0, y0 = np.clip(vis.min(0) - BOX_MARGIN, 0, 1)
    x1, y1 = np.clip(vis.max(0) + BOX_MARGIN, 0, 1)
    return [(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0]


def label_row(cls: str, kp: np.ndarray) -> str:
    return " ".join([cls] + [f"{b:.6g}" for b in keypoint_box(kp)] + [f"{x:.6g}" for x in kp.ravel()])


def copy_split(src: Path, dst: Path) -> int:
    """k6y7r images as they are; labels with the box recomputed from the keypoints."""
    shutil.copytree(src / "images", dst / "images")
    (dst / "labels").mkdir(parents=True)
    for label in (src / "labels").glob("*.txt"):
        rows = []
        for line in label.read_text().splitlines():
            v = line.split()
            if not v:
                continue
            rows.append(label_row(v[0], np.array(v[5:5 + 3 * K], float).reshape(K, 3)))
        (dst / "labels" / label.name).write_text("\n".join(rows) + "\n")
    return len(list((dst / "images").iterdir()))


def vnl_frames(clips: tuple[str, ...], every: int):
    """(label path, image path) of the VNL frames from the given clips, in frame order."""
    items = []
    for split in ("train", "valid", "test"):
        for label in (VNL / split / "labels").glob("*.txt"):
            clip, _, frame = label.stem.partition("_mp4-")
            if clip in clips:
                img = next((VNL / split / "images").glob(label.stem + ".*"))
                items.append((clip, int(frame[:4]), label, img))
    items.sort(key=lambda t: (t[0], t[2].name))
    by_clip = {}
    for clip, _, label, img in items:
        by_clip.setdefault(clip, []).append((label, img))
    return [x for c in clips for x in by_clip.get(c, [])[::every]]


def completed_label(label: Path, w: int, h: int) -> str:
    """One YOLO-pose row with all 10 floor points from the 4 labelled front-zone corners."""
    v = label.read_text().split()
    kp4 = np.array(v[5:], float).reshape(4, 3)
    floor = complete_floor(kp4[:, :2] * [w, h], FRONT_ZONE_IDS) / [w, h]
    kp = np.zeros((K, 3))
    inside = (floor[:, 0] >= 0) & (floor[:, 0] <= 1) & (floor[:, 1] >= 0) & (floor[:, 1] <= 1)
    kp[:10, :2] = np.where(inside[:, None], floor, 0)
    kp[:10, 2] = np.where(inside, 2, 0)
    return label_row(v[0], kp)


def add_vnl(dst: Path, clips: tuple[str, ...], every: int) -> int:
    (dst / "images").mkdir(parents=True, exist_ok=True)
    (dst / "labels").mkdir(parents=True, exist_ok=True)
    n = 0
    for label, img in vnl_frames(clips, every):
        h, w = cv2.imread(str(img)).shape[:2]
        (dst / "labels" / label.name).write_text(completed_label(label, w, h) + "\n")
        shutil.copy2(img, dst / "images" / img.name)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-drive", action="store_true", help="only build the local folder and zip")
    args = ap.parse_args()

    shutil.rmtree(OUT, ignore_errors=True)
    counts = {s: copy_split(K6Y7R / s, OUT / s) for s in ("train", "valid", "test")}
    counts["train (VNL clips one-three)"] = add_vnl(OUT / "train", VNL_TRAIN_CLIPS, VNL_TRAIN_EVERY)
    counts["test_vnl (clips four-five)"] = add_vnl(OUT / "test_vnl", VNL_TEST_CLIPS, 1)
    cfg = {
        "path": ".", "train": "train/images", "val": "valid/images", "test": "test/images",
        "kpt_shape": [K, 3], "flip_idx": K6Y7R_FLIP_IDX, "nc": 1, "names": ["volleyball-court"],
    }
    (OUT / "data.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    shutil.copy2(K6Y7R / "README.roboflow.txt", OUT / "LICENSE_k6y7r.txt")
    shutil.copy2(VNL / "README.roboflow.txt", OUT / "LICENSE_vnl.txt")
    print("images:", counts)

    zip_path = Path(shutil.make_archive(str(OUT), "zip", OUT.parent, OUT.name))
    print(f"zip: {zip_path} ({zip_path.stat().st_size / 1e6:.0f} MB)")
    if not args.no_drive:
        dst = drive_root() / DRIVE_RELPATH
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, dst)
        print(f"copied to Drive: {dst}")


if __name__ == "__main__":
    main()
