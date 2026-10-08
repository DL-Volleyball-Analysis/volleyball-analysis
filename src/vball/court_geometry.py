"""Geometric court registration (fallback / refinement, no training data).

Status: EXPERIMENTAL. On broadcast footage it is distracted by ad boards and railings
(1 of 5 test clips close to correct). The primary path will be a learned court
keypoint model (notebooks/train_court_keypoints.ipynb); this module is kept to
check and refine keypoint-based homographies.

Method: white-line mask -> Hough lines -> pair lines into court hypotheses ->
score each homography by overlap of the rendered court model with the line mask,
weighted by floor-colour uniformity inside the court.
"""
import itertools

import cv2
import numpy as np

from .court import CORNERS as OUTER
from .court import LINES

MODEL_LINES = list(LINES.values())


def line_mask(img):
    """Thin bright lines: white top-hat on lightness, low saturation."""
    hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
    l, s = hls[..., 1], hls[..., 2]
    k = max(9, img.shape[1] // 87) | 1
    tophat = cv2.morphologyEx(l, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    m = ((tophat > 18) & (s < 140)).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))


def long_lines(mask, min_len):
    """Probabilistic Hough on the line mask, then merge near-collinear segments."""
    hp = cv2.HoughLinesP(mask, 1, np.pi / 360, 80, minLineLength=min_len, maxLineGap=12)
    if hp is None:
        return []
    return merge_lines([tuple(map(float, h)) for h in hp.reshape(-1, 4)])


def to_homog(seg):
    x1, y1, x2, y2 = seg
    l = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
    return l / (np.linalg.norm(l[:2]) + 1e-9)


def merge_lines(segs, ang_tol=2.5, dist_tol=6.0):
    """Greedy merge of near-collinear segments; keeps total length as weight."""
    items = sorted(segs, key=lambda s: -np.hypot(s[2] - s[0], s[3] - s[1]))
    merged = []
    for s in items:
        a = np.degrees(np.arctan2(s[3] - s[1], s[2] - s[0])) % 180
        mid = np.array([(s[0] + s[2]) / 2, (s[1] + s[3]) / 2, 1.0])
        for m in merged:
            da = abs(a - m["ang"]); da = min(da, 180 - da)
            if da < ang_tol and abs(m["h"] @ mid) < dist_tol:
                m["len"] += np.hypot(s[2] - s[0], s[3] - s[1]); m["pts"] += [s[:2], s[2:]]
                break
        else:
            merged.append(dict(ang=a, h=to_homog(s), len=np.hypot(s[2] - s[0], s[3] - s[1]),
                               pts=[s[:2], s[2:]]))
    for m in merged:  # refit each merged line to its endpoints
        p = np.array(m["pts"], dtype=np.float32)
        vx, vy, x0, y0 = cv2.fitLine(p, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
        m["h"] = to_homog((x0, y0, x0 + vx, y0 + vy))
    return merged


def intersect(h1, h2):
    p = np.cross(h1, h2)
    return None if abs(p[2]) < 1e-9 else p[:2] / p[2]


def render(H, shape, thick):
    canvas = np.zeros(shape[:2], np.uint8)
    for a, b in MODEL_LINES:
        pts = np.linspace(a, b, 60).astype(np.float32).reshape(-1, 1, 2)
        q = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
        if not np.all(np.isfinite(q)):
            return None
        cv2.polylines(canvas, [q.astype(np.int32)], False, 255, thick)
    return canvas


def score(H, mask_dil, thick):
    r = render(H, mask_dil.shape, thick)
    if r is None:
        return -1, 0
    vis = int((r > 0).sum())
    if vis < 0.15 * (mask_dil.shape[0] + mask_dil.shape[1]):
        return -1, vis
    hit = int(((r > 0) & (mask_dil > 0)).sum())
    return hit / vis * np.sqrt(hit), vis   # precision weighted by evidence


def plausible(c, shape):
    """Court quad must be convex, reasonably large, and sit in the lower part of the frame."""
    h, w = shape[:2]
    if not cv2.isContourConvex(c.reshape(-1, 1, 2)):
        return False
    poly = c.copy(); poly[:, 0] = poly[:, 0].clip(0, w); poly[:, 1] = poly[:, 1].clip(0, h)
    area = cv2.contourArea(poly.reshape(-1, 1, 2))
    return area > 0.08 * w * h and poly[:, 1].mean() > 0.40 * h


def floor_uniformity(lab, H):
    """Inside each half court the floor is one colour: reward low colour spread (players are minority)."""
    h, w = lab.shape[:2]
    g = np.stack(np.meshgrid(np.linspace(0.5, 17.5, 24), np.linspace(0.5, 8.5, 12)), -1).reshape(-1, 1, 2)
    q = cv2.perspectiveTransform(g.astype(np.float32), H).reshape(-1, 2)
    ok = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
    if ok.mean() < 0.3:
        return 0.0
    px = lab[q[ok, 1].astype(int), q[ok, 0].astype(int)][:, 1:]   # a,b chroma only
    med = np.median(px, 0)
    inlier = (np.linalg.norm(px - med, axis=1) < 12).mean()          # share of samples near the floor colour
    return float(inlier) ** 2


def detect(img, top_k=7):
    h0, w0 = img.shape[:2]
    s = 960.0 / w0
    small = cv2.resize(img, (960, int(h0 * s)))
    mask = line_mask(small)
    lines = long_lines(mask, min_len=80)
    hh = small.shape[0]
    def mid_y(m):
        p = np.array(m["pts"]); return p[:, 1].mean()
    lines = [m for m in lines if mid_y(m) > 0.28 * hh]          # crowd / ad boards live at the top
    lines = sorted(lines, key=lambda m: -m["len"])[:24]
    if len(lines) < 4:
        return None
    # two orientation groups via 1-D k-means on doubled angle
    ang = np.array([m["ang"] for m in lines])
    v = np.stack([np.cos(np.radians(2 * ang)), np.sin(np.radians(2 * ang))], 1).astype(np.float32)
    _, lab, _ = cv2.kmeans(v, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-3), 5,
                           cv2.KMEANS_PP_CENTERS)
    g = [[m for m, l in zip(lines, lab.ravel()) if l == k][:top_k] for k in (0, 1)]
    mask_dil = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    small_lab = cv2.cvtColor(cv2.GaussianBlur(small, (5, 5), 0), cv2.COLOR_BGR2Lab).astype(np.float32)
    best = (-1, None)
    for A, B in itertools.permutations([0, 1]):          # which group runs along the 18 m length
        for la1, la2 in itertools.combinations(g[A], 2):  # long sides (sidelines)
            for lb1, lb2 in itertools.combinations(g[B], 2):  # short sides (end lines)
                c = [intersect(la1["h"], lb1["h"]), intersect(la1["h"], lb2["h"]),
                     intersect(la2["h"], lb2["h"]), intersect(la2["h"], lb1["h"])]
                if any(p is None for p in c):
                    continue
                c = np.float32(c)
                if np.abs(c).max() > 5000:
                    continue
                if not plausible(c, small.shape):
                    continue
                for corners in (c, c[[1, 0, 3, 2]]):      # both end-line orderings
                    H = cv2.getPerspectiveTransform(OUTER, corners)
                    sc, _ = score(H, mask_dil, 3)
                    if sc > 0:
                        sc *= floor_uniformity(small_lab, H)
                    if sc > best[0]:
                        best = (sc, H)
    if best[1] is None:
        return None
    S = np.diag([1 / s, 1 / s, 1.0])
    return dict(H=(S @ best[1]).tolist(), score=float(best[0]), mask=mask)
