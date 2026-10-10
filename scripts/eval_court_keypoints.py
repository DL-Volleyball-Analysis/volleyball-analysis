"""Court keypoint models measured in court metres, end to end.

For each labelled image: fit a homography from the model's floor keypoints with confidence >= 0.5 (RANSAC),
map the labelled floor points through it, and compare with their true court positions. This is the error a
landing call would see. Splits: `test` (k6y7r, all 10 floor points) and `test_vnl` (broadcast clips, the four
front-zone corners). Per clip for the broadcast split.

  .venv/bin/python scripts/eval_court_keypoints.py --model models/court_kpt_yolo26n_v2.pt
  .venv/bin/python scripts/eval_court_keypoints.py --model models/court_kpt_yolo26s_v3.pt --dataset court_keypoints_v3
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

from vball.court_keypoints import K6Y7R_FLOOR, VNL4_TO_K6Y7R
from vball.paths import DATASETS

FLOOR = np.float64(K6Y7R_FLOOR)
SPLITS = {"test": list(range(10)), "test_vnl": VNL4_TO_K6Y7R}


def train_imgsz(model) -> int:
    args = getattr(model, "overrides", {}) or {}
    return int(args.get("imgsz", 640))


def evaluate(model, root: Path, split: str, imgsz: int, conf_min: float = 0.5) -> dict:
    errs, per_clip, n, no_fit = [], {}, 0, 0
    for lp in sorted((root / split / "labels").glob("*.txt")):
        img_p = next((root / split / "images").glob(lp.stem + ".*"))
        img = cv2.imread(str(img_p))
        h, w = img.shape[:2]
        gt = np.array(lp.read_text().split()[5:5 + 42], float).reshape(14, 3)
        gt[:, 0] *= w
        gt[:, 1] *= h
        ids = [i for i in SPLITS[split] if gt[i, 2] > 0]
        if len(ids) < 4:
            continue
        n += 1
        r = model(img, verbose=False, imgsz=imgsz)[0]
        H = None
        if r.keypoints is not None and len(r.keypoints):
            kp = r.keypoints.data[int(r.boxes.conf.argmax())].cpu().numpy()
            use = [i for i in range(10) if kp[i, 2] >= conf_min]
            if len(use) >= 4:
                H, _ = cv2.findHomography(kp[use, :2].astype(np.float64), FLOOR[use], cv2.RANSAC, 0.01 * np.hypot(w, h))
        if H is None:
            no_fit += 1
            continue
        est = cv2.perspectiveTransform(gt[ids, :2].reshape(-1, 1, 2), H).reshape(-1, 2)
        e = np.linalg.norm(est - FLOOR[ids], axis=1)
        errs.extend(e)
        clip = lp.stem.split("_mp4")[0] if "_mp4" in lp.stem else "k6y7r"
        per_clip.setdefault(clip, []).extend(e)
    e = np.array(errs)
    return {"images": n, "no_fit": no_fit, "median": float(np.median(e)) if len(e) else None,
            "p90": float(np.percentile(e, 90)) if len(e) else None,
            "within_0.3": float(np.mean(e <= 0.3)) if len(e) else None,
            "per_clip": {c: float(np.median(v)) for c, v in sorted(per_clip.items())}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", default="court_keypoints_v3", help="folder under data/datasets")
    ap.add_argument("--imgsz", type=int, default=None, help="default: the model's training size")
    args = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(args.model)
    imgsz = args.imgsz or train_imgsz(model)
    print(f"model {Path(args.model).name}, dataset {args.dataset}, imgsz {imgsz}")
    for split in SPLITS:
        r = evaluate(model, DATASETS / args.dataset, split, imgsz)
        print(f"{split:9s} images {r['images']:4d}  no fit {r['no_fit']:3d}  median {r['median']:.2f} m  "
              f"p90 {r['p90']:.2f} m  within 0.3 m {r['within_0.3']:.0%}")
        if len(r["per_clip"]) > 1:
            for c, m in r["per_clip"].items():
                print(f"    {c:12s} median {m:.2f} m")


if __name__ == "__main__":
    main()
