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
import shutil
from pathlib import Path

from vball.datasets.jersey_crops import DRIVE_RELPATH, OUT, build
from vball.paths import drive_root


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
