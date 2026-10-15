"""Check court keypoint labels exported from CVAT ("CVAT for images 1.1", change add-labelling-loop).

Prints each label's problems and the floor fit, and writes an overlay per image (the court projected from the
labelled floor points, the points with their index) for inspection.

Usage:
  .venv/bin/python scripts/cvat_labels.py check annotations.xml --images outputs/court/personal_labels/plates \\
      --out outputs/court/personal_labels/overlays
"""

import argparse
import json
from pathlib import Path

import cv2

from vball.datasets import cvat


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("xml")
    c.add_argument("--images", required=True)
    c.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(args.xml)
    if src.suffix == ".json":  # compact JSON read from CVAT's REST API
        xml = src.with_suffix(".xml")
        xml.write_text(cvat.api_json_to_xml(json.loads(src.read_text())))
        src = xml
    labels = cvat.read_court_labels(src)
    for lab in labels:
        _, err, n = cvat.floor_fit(lab)
        problems = cvat.check(lab)
        placed = int((lab.points[:, 2] > 0).sum())
        status = "ok" if not problems else "; ".join(problems)
        print(f"{lab.image}: {placed}/14 points, {n} floor, median {err:.1f} px from the fit -> {status}")
        img = cv2.imread(str(Path(args.images) / lab.image))
        if img is not None:
            cv2.imwrite(str(out / lab.image), cvat.draw(img, lab))
    print(f"{len(labels)} labelled images")


if __name__ == "__main__":
    main()
