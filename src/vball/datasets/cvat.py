"""Court keypoint labels from CVAT (change add-labelling-loop).

Reads a "CVAT for images 1.1" export of the court-keypoints project: one `court` skeleton per image whose 14 points
are named k00..k13 in `vball.court_keypoints` order (k6y7r numbering). Each point becomes (x, y, visibility) with the
YOLO pose convention: 2 visible, 1 occluded (placed by the labeller from the lines), 0 outside (not placed).

Checks a label before it is used: the visible and occluded floor points must fit the court's homography; the median
reprojection error in pixels says whether a point was misplaced or the numbering is wrong.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from vball.court_keypoints import K6Y7R_FLOOR, K6Y7R_FLOOR_IDS

N_POINTS = 14
POINT_NAMES = [
    "k00_far_end_left",
    "k01_far_attack_left",
    "k02_far_centre",
    "k03_far_attack_right",
    "k04_far_end_right",
    "k05_near_end_right",
    "k06_near_attack_right",
    "k07_near_centre",
    "k08_near_attack_left",
    "k09_near_end_left",
    "k10_net_bottom_far",
    "k11_net_top_far",
    "k12_net_top_near",
    "k13_net_bottom_near",
]


@dataclass
class CourtLabel:
    image: str
    width: int
    height: int
    points: np.ndarray  # (14, 3): x, y, visibility (2 visible, 1 occluded, 0 outside)


def read_court_labels(xml_path: Path, label: str = "court") -> list[CourtLabel]:
    """Every image with a court skeleton; images without one are skipped (not labelled yet)."""
    out = []
    for img in ET.parse(xml_path).getroot().iter("image"):
        skel = next((s for s in img.iter("skeleton") if s.get("label") == label), None)
        if skel is None:
            continue
        pts = np.zeros((N_POINTS, 3), np.float32)
        for p in skel.iter("points"):
            name = p.get("label", "")
            if name not in POINT_NAMES:
                raise ValueError(f"{img.get('name')}: unknown point {name!r}")
            k = POINT_NAMES.index(name)
            if p.get("outside") == "1":
                continue
            x, y = (float(v) for v in p.get("points", "").split(";")[0].split(","))
            pts[k] = (x, y, 1 if p.get("occluded") == "1" else 2)
        out.append(CourtLabel(img.get("name", ""), int(img.get("width", 0)), int(img.get("height", 0)), pts))
    return out


def floor_residuals(lab: CourtLabel) -> tuple[np.ndarray | None, dict[int, float]]:
    """Homography court metres -> image from the placed floor points, and each point's error in pixels against a fit
    of the others (leave one out, so one misplaced point cannot hide by bending the fit)."""
    ids = [k for k in K6Y7R_FLOOR_IDS if lab.points[k, 2] > 0]
    if len(ids) < 4:
        return None, {}
    src = np.asarray(K6Y7R_FLOOR, np.float64)[ids]
    dst = lab.points[ids, :2].astype(np.float64)
    H, _ = cv2.findHomography(src, dst, 0)
    res = {}
    if len(ids) > 4:
        for i, k in enumerate(ids):
            keep = [j for j in range(len(ids)) if j != i]
            Hk, _ = cv2.findHomography(src[keep], dst[keep], 0)
            if Hk is not None:
                res[k] = float(np.linalg.norm(cv2.perspectiveTransform(src[i][None, None], Hk)[0, 0] - dst[i]))
    return H, res


def floor_fit(lab: CourtLabel) -> tuple[np.ndarray | None, float, int]:
    """(H, median leave-one-out error px, floor points used)."""
    H, res = floor_residuals(lab)
    n = int((lab.points[K6Y7R_FLOOR_IDS, 2] > 0).sum())
    return H, float(np.median(list(res.values()))) if res else float("nan"), n


def check(lab: CourtLabel, max_err_frac: float = 0.006) -> list[str]:
    """Problems with one label; an empty list means it can be used. A floor point is suspect when the others predict
    it more than 0.6% of the image width away (12 px at 1920; room for a phone lens's mild distortion)."""
    problems = []
    H, res = floor_residuals(lab)
    if H is None:
        n = int((lab.points[K6Y7R_FLOOR_IDS, 2] > 0).sum())
        problems.append(f"only {n} floor points placed (need 4)")
    for k, e in res.items():
        if e > max_err_frac * lab.width:
            problems.append(f"{POINT_NAMES[k]} does not fit the other floor points ({e:.0f} px)")
    for k in range(N_POINTS):
        x, y, v = lab.points[k]
        if v > 0 and not (0 <= x < lab.width and 0 <= y < lab.height):
            problems.append(f"{POINT_NAMES[k]} placed outside the image")
    return problems


def draw(img: np.ndarray, lab: CourtLabel) -> np.ndarray:
    """Overlay for inspection: the court projected from the floor fit (yellow), labelled points (green visible,
    orange occluded) with their index."""
    out = img.copy()
    H, _, _ = floor_fit(lab)
    if H is not None:
        from vball import court

        out = court.draw(out, H, thickness=2)
    for k in range(N_POINTS):
        x, y, v = lab.points[k]
        if v == 0:
            continue
        color = (0, 200, 0) if v == 2 else (0, 140, 255)
        cv2.circle(out, (int(x), int(y)), 6, color, 2)
        cv2.putText(out, str(k), (int(x) + 7, int(y) - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return out
