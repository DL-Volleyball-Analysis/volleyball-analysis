"""Build the jersey digit training set for Colab and zip it to Google Drive.

Replaces the capstone merge (training/jersey-numbers/organize_datasets.py), which mapped class indices across
datasets and ignored class names, so balls, whole players and whole-number boxes became the digits 0-2.

- Sources: the two volleyball Roboflow sets whose classes are digits (player crops, one box per digit), plus a
  baseball and football set with digit boxes, used for training only (more fonts, colours and poses; the
  valid and test splits stay volleyball). The capstone's two sets whose boxes are balls, players or whole
  numbers are left out.
- Classes are mapped by name: '0'-'9' (and 'cero', Spanish for zero) to the digit; any other class is dropped.
- Splits by match, not by frame: the Roboflow splits put frames of every match in both train and valid, so a
  validation score measured how well the model knows those shirts. Held-out matches are listed in SPLIT.

Usage: .venv/bin/python scripts/build_jersey_dataset.py [--no-drive]
"""
import argparse
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball.paths import DATASETS, drive_root  # noqa: E402

SOURCES = (DATASETS / "jersey-number-detection-s01j4-v1", DATASETS / "jersey-fxmll-v1", DATASETS / "jersey-number-cogss-v1")
TRAIN_ONLY = {"jersey-number-cogss-v1"}  # other sports: never in valid or test
OUT = DATASETS / "jersey_digits"
DRIVE_RELPATH = "volleyball/datasets/jersey_digits.zip"  # Colab: /content/drive/MyDrive/<this>
# Whole matches per split; every other match is training data. Test teams (Japan, Poland, Thailand) appear in no
# training match; valid needs two matches to contain every digit (one match has only its roster's numbers).
SPLIT = {"test": {"japan_poland", "thailand_warmup", "poland_italy"},
         "valid": {"usa_brazil_fem_brazilside", "usm_usach_1"}}
DIGITS = [str(d) for d in range(10)]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def digit_of(name: str) -> int | None:
    """The digit a Roboflow class name stands for, or None for a class that is not a digit."""
    name = name.strip().lower()
    if name in DIGITS:
        return int(name)
    return 0 if name == "cero" else None


def match_of(filename: str) -> str:
    """The match a Roboflow frame name comes from: 'chile_usa_cutted_f0_id2_jpg.rf.<hash>.jpg' -> 'chile_usa'.
    Parts of one match ('graz_1-2') belong to it ('graz_1')."""
    stem = re.sub(r"_(jpg|jpeg|png)\.rf\..*$", "", filename, flags=re.I)
    words = []
    for w in stem.split("_"):
        if w in ("cutted", "raw", "out") or (words and re.fullmatch(r"f\d+|id\d+|\d{2,}", w)):
            break
        words.append(w)
    return re.sub(r"-\d+$", "", "_".join(words))


def split_of(match: str) -> str:
    return next((s for s, matches in SPLIT.items() if match in matches), "train")


def relabel(text: str, mapping: dict[int, int | None]) -> str:
    """YOLO label lines with source class ids mapped to digits; lines of non-digit classes dropped."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if parts and mapping.get(int(parts[0])) is not None:
            out.append(" ".join([str(mapping[int(parts[0])]), *parts[1:]]))
    return "\n".join(out) + ("\n" if out else "")


def build(out: Path) -> dict[str, Counter]:
    shutil.rmtree(out, ignore_errors=True)
    boxes = {s: Counter() for s in ("train", "valid", "test")}
    images = Counter()
    for src in SOURCES:
        names = yaml.safe_load((src / "data.yaml").read_text())["names"]
        mapping = {i: digit_of(n) for i, n in enumerate(names)}
        for img in sorted(src.glob("*/images/*")):
            if img.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            label = img.parent.parent / "labels" / f"{img.stem}.txt"
            text = relabel(label.read_text() if label.exists() else "", mapping)
            if not text:
                continue  # no digit on this crop
            split = "train" if src.name in TRAIN_ONLY else split_of(match_of(img.name))
            name = f"{src.name}_{img.name}"
            (out / split / "images").mkdir(parents=True, exist_ok=True)
            (out / split / "labels").mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, out / split / "images" / name)
            (out / split / "labels" / f"{Path(name).stem}.txt").write_text(text)
            images[split] += 1
            boxes[split].update(int(line.split()[0]) for line in text.splitlines())
    cfg = {"path": ".", "train": "train/images", "val": "valid/images", "test": "test/images",
           "nc": 10, "names": DIGITS}
    (out / "data.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    for src in SOURCES:
        shutil.copy2(src / "README.roboflow.txt", out / f"LICENSE_{src.name}.txt")
    return {"images": images, **boxes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-drive", action="store_true", help="only build the local folder and zip")
    args = ap.parse_args()
    counts = build(OUT)
    print("images:", dict(counts["images"]))
    for split in ("train", "valid", "test"):
        c = counts[split]
        print(f"{split:5s} boxes per digit:", " ".join(f"{d}:{c[d]}" for d in range(10)))
        missing = [d for d in range(10) if c[d] == 0]
        if missing:
            raise SystemExit(f"{split} has no boxes for digits {missing}; change SPLIT")
    zip_path = Path(shutil.make_archive(str(OUT), "zip", OUT.parent, OUT.name))
    print(f"zip: {zip_path} ({zip_path.stat().st_size / 1e6:.0f} MB)")
    if not args.no_drive:
        dst = drive_root() / DRIVE_RELPATH
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, dst)
        print(f"copied to Drive: {dst}")


if __name__ == "__main__":
    main()
