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


def api_json_to_xml(data: dict) -> str:
    """CVAT for images 1.1 XML from the compact JSON the labelling page posts (frames: [name, width, height];
    shapes: frame, label, el: [point name, x, y, outside, occluded]) read from CVAT's REST API."""
    by_frame: dict[int, list[dict]] = {}
    for shape in data["shapes"]:
        by_frame.setdefault(shape["frame"], []).append(shape)
    parts = ["<annotations>"]
    for i, (name, w, h) in enumerate(data["frames"]):
        parts.append(f'<image id="{i}" name="{name}" width="{w}" height="{h}">')
        for shape in by_frame.get(i, []):
            pts = "".join(
                f'<points label="{n}" outside="{o}" occluded="{c}" points="{x},{y}"></points>'
                for n, x, y, o, c in shape["el"]
            )
            parts.append(f'<skeleton label="{shape["label"]}">{pts}</skeleton>')
        parts.append("</image>")
    parts.append("</annotations>")
    return "".join(parts)


# Points that lie on one straight line in the world, so also in an undistorted image: the far and near sidelines, then
# the net post above each centre point (net bottom and top). A post line goes through its centre point as already
# placed on the sideline, which is better supported (five points) than the net points.
STRAIGHT_LINES = [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [2, 10, 11], [7, 13, 12]]


def straighten(lab: CourtLabel) -> tuple[CourtLabel, dict[int, float]]:
    """The label with each point moved perpendicular onto the line fitted (total least squares) through its group in
    `STRAIGHT_LINES`, and how far each point moved in px. Only groups with at least three placed points are changed;
    a point's position along its line is the labeller's, so the court's measurements are not imposed."""
    pts = lab.points.copy()
    moved: dict[int, float] = {}
    for group in STRAIGHT_LINES:
        ids = [k for k in group if lab.points[k, 2] > 0]
        if len(ids) < 3:
            continue
        xy = pts[ids, :2].astype(np.float64)
        post = group[0] in (2, 7) and group[0] in ids
        c = xy[0] if post else xy.mean(0)  # a post line keeps its centre point fixed
        d = np.linalg.svd(xy - c)[2][0]
        proj = c + np.outer((xy - c) @ d, d)
        for k, q in zip(ids[1:] if post else ids, proj[1:] if post else proj):
            moved[k] = moved.get(k, 0.0) + float(np.linalg.norm(q - pts[k, :2]))
            pts[k, :2] = q
    return CourtLabel(lab.image, lab.width, lab.height, pts), moved


def yolo_keypoints(lab: CourtLabel) -> np.ndarray:
    """(14, 3) keypoints normalised to the image for a YOLO pose label: x, y, visibility. Points placed outside the
    image count as not labelled (visibility 0, coordinates 0); occluded points keep visibility 1."""
    kp = lab.points.astype(np.float64).copy()
    inside = (kp[:, 0] >= 0) & (kp[:, 0] < lab.width) & (kp[:, 1] >= 0) & (kp[:, 1] < lab.height)
    kp[~inside | (kp[:, 2] == 0)] = 0
    kp[:, 0] /= lab.width
    kp[:, 1] /= lab.height
    return kp


def floor_residuals(lab: CourtLabel) -> tuple[np.ndarray | None, dict[int, float]]:
    """Homography court metres -> image from the placed floor points, and each point's distance in pixels from it.

    Leave-one-out errors were tried first and rejected: a point with no neighbour nearby (the one corner close to the
    camera) is extrapolated from far points and gets a large error even when it is right (167 px on a correct label).
    """
    ids = [k for k in K6Y7R_FLOOR_IDS if lab.points[k, 2] > 0]
    if len(ids) < 4:
        return None, {}
    src = np.asarray(K6Y7R_FLOOR, np.float64)[ids]
    dst = lab.points[ids, :2].astype(np.float64)
    H, _ = cv2.findHomography(src, dst, 0)
    if H is None:
        return None, {}
    err = np.linalg.norm(cv2.perspectiveTransform(src[None], H)[0] - dst, axis=1)
    return H, {k: float(e) for k, e in zip(ids, err)} if len(ids) > 4 else {}


def floor_fit(lab: CourtLabel) -> tuple[np.ndarray | None, float, int]:
    """(H, median distance of the floor points from the fit in px, floor points used)."""
    H, res = floor_residuals(lab)
    n = int((lab.points[K6Y7R_FLOOR_IDS, 2] > 0).sum())
    return H, float(np.median(list(res.values()))) if res else float("nan"), n


def check(lab: CourtLabel, max_err_frac: float = 0.006) -> list[str]:
    """Problems with one label; an empty list means it can be used. A floor point is suspect when it lies more than
    0.6% of the image width (12 px at 1920) from the court fitted to all floor points; the margin leaves room for a
    phone lens's distortion, which a homography cannot model."""
    problems = []
    H, res = floor_residuals(lab)
    n = int((lab.points[K6Y7R_FLOOR_IDS, 2] > 0).sum())
    if H is None and n < 4:
        problems.append(f"only {n} floor points placed (need 4 to check them)")
    # n >= 4 without a fit: all on one sideline (a low side camera sees only the far one). The label is valid for
    # training but cannot be checked here.
    for k, e in res.items():
        if e > max_err_frac * lab.width:
            problems.append(f"{POINT_NAMES[k]} does not fit the other floor points ({e:.0f} px)")
    for k in range(N_POINTS):
        x, y, v = lab.points[k]
        if v > 0 and not (0 <= x < lab.width and 0 <= y < lab.height):
            problems.append(f"{POINT_NAMES[k]} placed outside the image (mark it outside instead)")
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
