"""Camera calibration on the k6y7r test split: from the labelled keypoints and from model predictions.

For each image, `vball.calibration.calibrate` runs on (a) the labelled keypoints with visibility > 0 and
(b) the court model's keypoints with confidence >= 0.5. Reports the status counts, the median
reprojection error (pixels and % of image width), and the recovered camera height and focal length.

  .venv/bin/python scripts/eval_calibration.py [--model models/court_kpt_yolo26n_v2.pt] [--split test]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from vball.calibration import calibrate
from vball.paths import DATASETS, MODELS

DATASET = DATASETS / "court_keypoints_v3"
K = 14


def labelled_points(label: Path, w: int, h: int) -> np.ndarray:
    row = [float(x) for x in label.read_text().split()]
    kp = np.array(row[5:5 + 3 * K]).reshape(K, 3)
    pts = kp[:, :2] * [w, h]
    pts[kp[:, 2] <= 0] = np.nan
    return pts


def predicted_points(model, image: np.ndarray, min_conf: float = 0.5) -> np.ndarray:
    r = model.predict(image, verbose=False)[0]
    pts = np.full((K, 2), np.nan)
    if r.keypoints is None or len(r.keypoints) == 0:
        return pts
    i = int(r.boxes.conf.argmax())
    xy = r.keypoints.xy[i].cpu().numpy()
    conf = r.keypoints.conf[i].cpu().numpy()
    pts[conf >= min_conf] = xy[conf >= min_conf]
    return pts


def summarise(name: str, cals: list, widths: list[int]) -> None:
    statuses = [c.status for c in cals]
    counts = {s: statuses.count(s) for s in ("ok", "floor_only", "unusable")}
    used = [(c, w) for c, w in zip(cals, widths) if c.status != "unusable"]
    print(f"\n{name}: {len(cals)} images, " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    if not used:
        return
    err = np.array([c.reprojection_px for c, _ in used])
    rel = np.array([100 * c.reprojection_px / w for c, w in used])
    height = np.array([c.camera.position[2] for c, _ in used])
    fov = np.array([np.degrees(2 * np.arctan(w / 2 / c.camera.focal)) for c, w in used])
    print(f"  reprojection error: median {np.median(err):.2f} px ({np.median(rel):.2f}% of width), "
          f"p90 {np.quantile(err, 0.9):.2f} px")
    print(f"  camera height: median {np.median(height):.1f} m; horizontal field of view: median {np.median(fov):.0f} deg")
    nets = [c.net_top for c, _ in used if c.net_top is not None]
    if nets:
        print(f"  net height chosen: 2.43 m in {nets.count(2.43)}, 2.24 m in {nets.count(2.24)}")
    def kind(reason: str) -> str:
        for key, label in (("floor keypoints", "fewer than 4 floor keypoints"), ("one line", "floor points on one line"),
                           ("focal length", "focal length poorly constrained"), ("reprojection", "reprojection error above the gate"),
                           ("below the floor", "camera below the floor"), ("pose", "no pose")):
            if key in reason:
                return label
        return reason
    kinds = [kind(c.reason) for c in cals if c.status == "unusable"]
    for k in sorted(set(kinds), key=kinds.count, reverse=True):
        print(f"  unusable: {k}: {kinds.count(k)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(MODELS / "court_kpt_yolo26n_v2.pt"))
    ap.add_argument("--split", default="test")
    args = ap.parse_args()

    images = sorted((DATASET / args.split / "images").glob("*.jpg"))
    from ultralytics import YOLO
    model = YOLO(args.model)
    labelled, predicted, widths = [], [], []
    for img_path in images:
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        widths.append(w)
        label = DATASET / args.split / "labels" / (img_path.stem + ".txt")
        labelled.append(calibrate(labelled_points(label, w, h), (w, h)))
        predicted.append(calibrate(predicted_points(model, img), (w, h)))
    print(f"k6y7r {args.split} split ({DATASET.name}), {len(images)} images; model {Path(args.model).name}")
    summarise("from labelled keypoints", labelled, widths)
    summarise("from model keypoints (conf >= 0.5)", predicted, widths)


if __name__ == "__main__":
    main()
