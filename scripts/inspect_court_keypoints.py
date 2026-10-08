"""Draw numbered keypoints on sample images of a YOLO-pose dataset and print visibility stats.

Usage: .venv/bin/python scripts/inspect_court_keypoints.py <dataset_dir> [n_samples]
Overlays go to outputs/court_keypoints_inspect/<dataset_name>/.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball.paths import OUTPUTS  # noqa: E402


def load_labels(label_path: Path, k: int) -> np.ndarray:
    rows = [list(map(float, l.split())) for l in label_path.read_text().splitlines() if l.strip()]
    return np.array([r[5:5 + 3 * k] for r in rows]).reshape(-1, k, 3)


def main():
    root = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    k = yaml.safe_load((root / "data.yaml").read_text())["kpt_shape"][0]
    out = OUTPUTS / "court_keypoints_inspect" / root.name
    out.mkdir(parents=True, exist_ok=True)

    labels = sorted(root.glob("*/labels/*.txt"))
    vis = np.zeros((k, 3), int)
    for p in labels:
        for inst in load_labels(p, k):
            for i, v in enumerate(inst[:, 2].astype(int)):
                vis[i, v] += 1
    print(f"{len(labels)} label files, {k} keypoints; visibility counts (0 absent / 1 occluded / 2 visible):")
    for i in range(k):
        print(f"  kp{i:2d}: {vis[i].tolist()}")

    rng = np.random.default_rng(0)
    for p in rng.choice(labels, size=min(n, len(labels)), replace=False):
        img_path = next(p.parent.parent.joinpath("images").glob(p.stem + ".*"))
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        for inst in load_labels(p, k):
            for i, (x, y, v) in enumerate(inst):
                if v == 0:
                    continue
                c = (0, 255, 0) if v == 2 else (0, 165, 255)
                pt = (int(x * w), int(y * h))
                cv2.circle(img, pt, 5, c, -1)
                cv2.putText(img, str(i), (pt[0] + 6, pt[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
                cv2.putText(img, str(i), (pt[0] + 6, pt[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, 2)
        cv2.imwrite(str(out / f"{img_path.stem[:40]}.jpg"), img)
    print(f"overlays -> {out}")


if __name__ == "__main__":
    main()
