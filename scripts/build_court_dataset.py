"""Build the court keypoint training set (v4; v3b with --no-cvat) and zip it for Kaggle or Colab.

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
- CVAT labels (v4, change add-labelling-loop): our own court labels in data/datasets/court_cvat (images and the
  job exports), straightened along the sidelines and net posts (`cvat.straighten`). Split by recording, never by
  frame: the owner's own recordings (personal_*) and six amateur videos are `test_amateur`, five more amateur videos
  join `valid`, the rest and the broadcast frames join `train`, amateur images repeated 3 times so 30 images are not
  drowned by 700. The Watchdog end-line plates are `test_watchdog` (their arenas may appear in the fixed test clips).
- Numbering (v4): every label in every split is renumbered by `canonical_numbering` (a court looks the same turned
  by 180 degrees; k6y7r numbers end-line views one way, our labels and ultralytics' flip with a fixed flip_idx the
  other). Mirror augmentation is therefore done here, not in training (train with fliplr=0): every train image also
  gets a mirrored copy, flipped, permuted and renumbered by the same rule.

Usage: .venv/bin/python scripts/build_court_dataset.py [--no-drive] [--no-cvat]
"""

import argparse
import hashlib
import re
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml

from vball.court_keypoints import FRONT_ZONE_IDS, K6Y7R_FLIP_IDX, canonical_numbering, complete_floor
from vball.datasets import cvat
from vball.paths import DATASETS, drive_root

K6Y7R = DATASETS / "volleyball-court-keypoints-k6y7r-v1"
VNL = DATASETS / "volleyball_court_key_points_regression_dataset-v7"
CVAT = DATASETS / "court_cvat"
AMATEUR_TEST, AMATEUR_VALID, AMATEUR_REPEAT = 6, 5, 3
VNL_TRAIN_CLIPS = ("clip_one", "clip_two", "clip_three")
VNL_TEST_CLIPS = ("clip_four", "clip_five")
VNL_TRAIN_EVERY = 2  # consecutive frames are near duplicates; keep VNL from outweighing k6y7r


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


def canonical(kp: np.ndarray, w: int, h: int) -> np.ndarray:
    """`canonical_numbering` of a normalised label (the rule is defined in pixels)."""
    px = kp * [w, h, 1]
    return canonical_numbering(px) / [w, h, 1]


def renumber_split(split_dir: Path) -> int:
    """Rewrite every label of a split in the canonical numbering; returns how many labels changed."""
    changed = 0
    for label in sorted((split_dir / "labels").glob("*.txt")):
        h, w = cv2.imread(str(next((split_dir / "images").glob(label.stem + ".*")))).shape[:2]
        rows = []
        for line in label.read_text().splitlines():
            v = line.split()
            kp = np.array(v[5:], float).reshape(K, 3)
            new = canonical(kp, w, h)
            changed += int(not np.allclose(new, kp))
            rows.append(label_row(v[0], new))
        label.write_text("\n".join(rows) + "\n")
    return changed


def add_mirrors(split_dir: Path) -> int:
    """A mirrored copy of every image of the split, labels flipped, permuted and renumbered."""
    n = 0
    for label in sorted((split_dir / "labels").glob("*.txt")):
        src = next((split_dir / "images").glob(label.stem + ".*"))
        img = cv2.flip(cv2.imread(str(src)), 1)
        h, w = img.shape[:2]
        rows = []
        for line in label.read_text().splitlines():
            v = line.split()
            kp = np.array(v[5:], float).reshape(K, 3)
            kp[:, 0] = np.where(kp[:, 2] > 0, 1 - kp[:, 0], 0)
            rows.append(label_row(v[0], canonical(kp[K6Y7R_FLIP_IDX], w, h)))
        cv2.imwrite(str(split_dir / "images" / f"{label.stem}_mirror{src.suffix}"), img)
        (split_dir / "labels" / f"{label.stem}_mirror.txt").write_text("\n".join(rows) + "\n")
        n += 1
    return n


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
            rows.append(label_row(v[0], np.array(v[5 : 5 + 3 * K], float).reshape(K, 3)))
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


def cvat_split(image: str, amateur_rank: dict[str, int]) -> str:
    """Split of one CVAT image, decided by its recording."""
    if image.startswith("test_watchdog"):
        return "test_watchdog"
    if image.startswith("personal_"):
        return "test_amateur"
    if image.startswith("train_amateur_"):
        r = amateur_rank[image]
        return "test_amateur" if r < AMATEUR_TEST else "valid" if r < AMATEUR_TEST + AMATEUR_VALID else "train"
    return "train"


def add_cvat(out: Path) -> dict[str, int]:
    """Our CVAT court labels, straightened, as YOLO pose labels (images as JPEG)."""
    labels = [lab for xml in sorted((CVAT / "annotations").glob("*.xml")) for lab in cvat.read_court_labels(xml)]
    # a fixed pseudo-random order of the amateur recordings (one image per recording), the same on every build
    amateur = sorted(
        (lab.image for lab in labels if lab.image.startswith("train_amateur_")),
        key=lambda n: hashlib.md5(n.encode()).hexdigest(),
    )
    rank = {n: i for i, n in enumerate(amateur)}
    counts: dict[str, int] = {}
    for lab in labels:
        split = cvat_split(lab.image, rank)
        kp = cvat.yolo_keypoints(cvat.straighten(lab)[0])
        if (kp[:, 2] > 0).sum() < 4:
            continue
        img = cv2.imread(str(CVAT / "images" / lab.image))
        repeat = AMATEUR_REPEAT if split == "train" and lab.image.startswith("train_amateur_") else 1
        stem = re.sub(r"\.[a-z]+$", "", lab.image)
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        for r in range(repeat):
            name = f"cvat_{stem}" + (f"_r{r}" if r else "")
            cv2.imwrite(str(out / split / "images" / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            (out / split / "labels" / f"{name}.txt").write_text(label_row("0", kp) + "\n")
        counts[split] = counts.get(split, 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-drive", action="store_true", help="only build the local folder and zip")
    ap.add_argument("--no-cvat", action="store_true", help="v3b: without our CVAT labels")
    args = ap.parse_args()
    name = "court_keypoints_v3b" if args.no_cvat else "court_keypoints_v4"
    out = DATASETS / name

    shutil.rmtree(out, ignore_errors=True)
    counts = {s: copy_split(K6Y7R / s, out / s) for s in ("train", "valid", "test")}
    counts["train (VNL clips one-three)"] = add_vnl(out / "train", VNL_TRAIN_CLIPS, VNL_TRAIN_EVERY)
    counts["test_vnl (clips four-five)"] = add_vnl(out / "test_vnl", VNL_TEST_CLIPS, 1)
    if not args.no_cvat:
        counts.update({f"{k} (CVAT, recordings)": v for k, v in add_cvat(out).items()})
        for split_dir in sorted(p for p in out.iterdir() if p.is_dir()):
            counts[f"{split_dir.name} renumbered"] = renumber_split(split_dir)
        counts["train mirrored copies"] = add_mirrors(out / "train")
    cfg = {
        "path": ".",
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "kpt_shape": [K, 3],
        "flip_idx": K6Y7R_FLIP_IDX,
        "nc": 1,
        "names": ["volleyball-court"],
    }
    (out / "data.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    shutil.copy2(K6Y7R / "README.roboflow.txt", out / "LICENSE_k6y7r.txt")
    shutil.copy2(VNL / "README.roboflow.txt", out / "LICENSE_vnl.txt")
    print("images:", counts)

    zip_path = Path(shutil.make_archive(str(out), "zip", out.parent, out.name))
    print(f"zip: {zip_path} ({zip_path.stat().st_size / 1e6:.0f} MB)")
    if not args.no_drive:
        dst = drive_root() / "volleyball/datasets" / f"{name}.zip"  # Colab: /content/drive/MyDrive/volleyball/...
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, dst)
        print(f"copied to Drive: {dst}")


if __name__ == "__main__":
    main()
