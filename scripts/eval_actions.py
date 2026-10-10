"""The capstone action recogniser on its dataset's test split, plus how much the test split shares source
videos with the training split.

Roboflow names frames "<video>_mp4-<frame>_jpg.rf.<hash>.jpg"; frames of one video in both splits are near
duplicates, which makes a test score optimistic for unseen matches. The overlap is reported next to the score.

  .venv/bin/python scripts/eval_actions.py [--model models/action_yolo11m.pt]
      [--data data/datasets/volleyball_actions_capstone] [--train-zip <capstone zip with the train split>]
"""
import argparse
import re
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import yaml

from vball.paths import DATASETS, MODELS


def source(name: str) -> str:
    """The source video of a Roboflow frame name ('' when the name has no video part)."""
    stem = Path(name).name
    m = re.match(r"(.+?)_(mp4|mov|avi|MP4|MOV)[-_]", stem)
    return m.group(1) if m else ""


def label_stats(label_texts: list[str], n_classes: int) -> dict:
    """Boxes per class, images per class, images without any box, boxes per image."""
    boxes, images, empty, per_image = [0] * n_classes, [0] * n_classes, 0, []
    for t in label_texts:
        cls = [int(line.split()[0]) for line in t.splitlines() if line.strip()]
        per_image.append(len(cls))
        if not cls:
            empty += 1
        for c in cls:
            boxes[c] += 1
        for c in set(cls):
            images[c] += 1
    return {"images": len(label_texts), "empty": empty, "boxes": boxes, "images_with": images,
            "max_per_image": max(per_image) if per_image else 0}


def print_distribution(split: str, st: dict, names: list[str]) -> None:
    total = sum(st["boxes"])
    print(f"{split:6s} {st['images']:6d} images, {total:6d} boxes, {st['empty']} images without a box "
          f"({st['empty'] / max(1, st['images']):.1%}), up to {st['max_per_image']} boxes in one image")
    for c, name in enumerate(names):
        print(f"    {name:8s} {st['boxes'][c]:6d} boxes ({st['boxes'][c] / max(1, total):5.1%}) in {st['images_with'][c]:6d} images")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(MODELS / "action_yolo11m.pt"))
    ap.add_argument("--data", default=str(DATASETS / "volleyball_actions_capstone"))
    ap.add_argument("--train-zip", default=None, help="capstone zip, to list the training frames' videos")
    ap.add_argument("--prefix", default="vb_action_yolov11/Volleyball_Action_Dataset/train/images/")
    args = ap.parse_args()

    root = Path(args.data)
    names = yaml.safe_load((root / "data.yaml").read_text())["names"]
    print("class distribution")
    if args.train_zip:
        z = zipfile.ZipFile(args.train_zip)
        base = args.prefix.rsplit("/train/", 1)[0]
        for split in ("train", "valid"):
            files = [n for n in z.namelist() if n.startswith(f"{base}/{split}/labels/") and n.endswith(".txt")]
            print_distribution(split, label_stats([z.read(n).decode() for n in files], len(names)), names)
    test_labels = sorted((root / "test" / "labels").glob("*.txt"))
    print_distribution("test", label_stats([p.read_text() for p in test_labels], len(names)), names)
    test = sorted((root / "test" / "images").glob("*.jpg")) + sorted((root / "test" / "images").glob("*.png"))
    print(f"test split: {len(test)} images")
    if args.train_zip:
        train = [n for n in zipfile.ZipFile(args.train_zip).namelist() if n.startswith(args.prefix) and not n.endswith("/")]
        train_videos = Counter(source(n) for n in train)
        test_src = [source(p.name) for p in test]
        named = [s for s in test_src if s]
        shared = sum(1 for s in named if s in train_videos)
        print(f"training split: {len(train)} images from {len(train_videos)} named sources")
        print(f"test images with a source video name: {len(named)}; of those, from a video also in training: "
              f"{shared} ({shared / max(1, len(named)):.0%})")

    from ultralytics import YOLO
    cfg = yaml.safe_load((root / "data.yaml").read_text())
    cfg.update({"path": str(root.resolve()), "test": "test/images", "val": "test/images", "train": "test/images"})
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
    m = YOLO(args.model).val(data=f.name, split="test", imgsz=640, batch=8, plots=False, verbose=False)
    print(f"\ntest mAP@0.5 {m.box.map50:.3f}, mAP@0.5:0.95 {m.box.map:.3f}, precision {m.box.mp:.3f}, recall {m.box.mr:.3f}")
    for i, c in enumerate(m.box.ap_class_index):
        print(f"  {names[int(c)]:8s} AP@0.5 {m.box.ap50[i]:.3f}  AP@0.5:0.95 {m.box.ap[i]:.3f}")


if __name__ == "__main__":
    main()
