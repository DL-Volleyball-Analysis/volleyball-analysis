"""Court from painted lines: a court model fitted to the lines of an image, for cameras that stay still.

A still camera sees the same floor for a whole shot, so the per-pixel median of frames spread over the shot
(`background_plate`) is an empty court: players, ball and referees move and disappear, the painted lines stay. On that
plate (change verify-court-by-lines, design):

1. Line pixels (`line_pixels`): brighter by `t` than the pixels `tau` away on both sides, horizontally or vertically
   (Farin et al. 2003); with `dark=True` darker instead (some multi-sport floors paint volleyball lines black).
   Connected parts that are short, or thick and filling their bounding box (text, logos, wood grain), are dropped.
2. Line candidates (`candidates`): Hough segments merged into lines and split into two direction families.
3. Court fit (`fit`): two lines of one family as the sidelines, two of the other as cross lines at court positions
   CROSS_X (all ordered pairs), both family roles; each hypothesis is a homography from the four intersections.
   Implausible courts, courts under MIN_AREA of the image, fans or slivers (`well_shaped`) and fits that imply no
   sensible camera (`seen_from_a_camera`) are rejected; the rest are scored by `line_score`.

`line_score` is also how a court found another way (the keypoint model) is compared with the line fit on the same
plate. All work happens at WORK_WIDTH; homographies are returned in the input image's pixels (court metres -> image).
"""

import itertools
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .court import LINES
from .court_keypoints import corners_from_homography, court_is_plausible

WORK_WIDTH = 1280
CROSS_X = (0.0, 6.0, 9.0, 12.0, 18.0)  # end, attack, centre, attack, end line
SIDE_Y = (0.0, 9.0)
MIN_AREA = 0.08  # of the image
MIN_ANGLE_DEG = 25.0  # every interior angle of the projected court
MIN_SIDE = 0.10  # every side, of the image width
MAX_VANISHING = 20.0  # a floor seen from above: some court direction vanishes within this many image widths
MAX_HORIZON_TILT = 30.0  # degrees from horizontal for the floor's horizon (camera roll)
SUPPORT_PX = 3.0  # a line sample within this of a line pixel is supported (at WORK_WIDTH)
STEP_PX = 6.0  # line sampling step (at WORK_WIDTH)
FLAT_DEG = 25.0  # line families: within this of horizontal, or steeper
MAX_SIDES, MAX_CROSS = 12, 14  # longest candidates tried per family


@dataclass
class Fit:
    H: np.ndarray  # court metres -> input image pixels
    score: float
    supported: int  # line samples on painted lines
    samples: int
    good_lines: int  # court lines with at least half their samples supported
    dark: bool  # fitted to dark lines

    @property
    def support(self) -> float:
        return self.supported / self.samples if self.samples else 0.0


def background_plate(video: Path, start: int, end: int, n: int = 60) -> np.ndarray | None:
    """Per-pixel median of n frames spread evenly over [start, end]: the empty court for a still camera."""
    cap = cv2.VideoCapture(str(video))
    frames = []
    for f in np.unique(np.linspace(start, end, n).astype(int)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
    cap.release()
    return np.median(np.stack(frames), axis=0).astype(np.uint8) if frames else None


def line_pixels(img: np.ndarray, tau: int = 6, t: int = 18, dark: bool = False) -> np.ndarray:
    """uint8 mask of thin painted-line pixels (see module doc)."""
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.int16)
    if dark:
        g = -g

    def shifted(dx, dy):
        return np.roll(np.roll(g, dy, 0), dx, 1)

    hor = (g - shifted(tau, 0) > t) & (g - shifted(-tau, 0) > t)
    ver = (g - shifted(0, tau) > t) & (g - shifted(0, -tau) > t)
    m = hor | ver
    if not dark:  # white lines are unsaturated; coloured logos are not
        m &= cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1] < 90
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    w, h, a = st[:, 2], st[:, 3], st[:, 4]
    long_side = np.maximum(np.maximum(w, h), 1)
    # thin (mean thickness along the long side at most 10 px: an axis-aligned line fills its box) or sparse in its box
    keep = (long_side >= 25) & ((a / long_side <= 10) | (a < 0.35 * w * h + 40))
    keep[0] = False
    return keep[lab].astype(np.uint8)


def candidates(mask: np.ndarray, min_len: float = 120.0) -> list[dict]:
    """Lines {"l": homogeneous line (unit normal), "ang": degrees in [0, 180), "len": summed segment length}."""
    seg = cv2.HoughLinesP(mask * 255, 1, np.pi / 360, 80, minLineLength=80, maxLineGap=15)
    if seg is None:
        return []
    out = []
    for s in sorted(seg.reshape(-1, 4).astype(float), key=lambda s: -np.hypot(s[2] - s[0], s[3] - s[1])):
        length = np.hypot(s[2] - s[0], s[3] - s[1])
        hom = np.cross([s[0], s[1], 1.0], [s[2], s[3], 1.0])
        hom /= np.linalg.norm(hom[:2])
        ang = np.degrees(np.arctan2(s[3] - s[1], s[2] - s[0])) % 180
        mid = np.array([(s[0] + s[2]) / 2, (s[1] + s[3]) / 2, 1.0])
        for o in out:
            if min(abs(ang - o["ang"]), 180 - abs(ang - o["ang"])) < 2.0 and abs(o["l"] @ mid) < 8.0:
                o["len"] += length
                break
        else:
            out.append({"l": hom, "ang": ang, "len": length})
    return [o for o in out if o["len"] >= min_len]


def well_shaped(corners: np.ndarray, width: int) -> bool:
    """No fans or slivers: every interior angle at least MIN_ANGLE_DEG and every side at least MIN_SIDE of the width
    (a camera above the floor never sees the court as a fan)."""
    c = np.asarray(corners, float)
    for i in range(4):
        a, b = c[i - 1] - c[i], c[(i + 1) % 4] - c[i]
        if np.linalg.norm(b) < MIN_SIDE * width:
            return False
        cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        if np.degrees(np.arccos(np.clip(cos, -1, 1))) < MIN_ANGLE_DEG:
            return False
    return True


def seen_from_a_camera(H: np.ndarray, size: tuple[int, int]) -> bool:
    """The fit looks like a floor seen from a camera above it: perspective (the sidelines or the cross lines converge,
    some court direction vanishing within MAX_VANISHING image widths of the centre), a horizon (the image of the
    floor's line at infinity) within MAX_HORIZON_TILT of horizontal, and the court below that horizon. A wall panel or
    a scoreboard has a steep horizon or none. (The focal length is no test: a symmetric end-line view leaves it
    undetermined.)"""
    w, h = size
    H = np.asarray(H, float)
    centre = np.array([w / 2, h / 2])
    vanishes = False
    for d in (np.array([1.0, 0, 0]), np.array([0, 1.0, 0])):
        v = H @ d
        vanishes |= abs(v[2]) > 1e-12 and np.linalg.norm(v[:2] / v[2] - centre) < MAX_VANISHING * w
    if not vanishes:
        return False
    horizon = np.linalg.inv(H).T @ np.array([0, 0, 1.0])  # a, b, c of a u + b v + c = 0
    a, b = horizon[0], horizon[1]
    if abs(b) < 1e-12 or np.degrees(np.arctan2(abs(a), abs(b))) > MAX_HORIZON_TILT:
        return False
    corners = corners_from_homography(H)
    horizon_v = -(a * corners[:, 0] + horizon[2]) / b
    return bool((corners[:, 1] > horizon_v).all())  # image v grows downwards: the court lies below the horizon


def _area(c: np.ndarray) -> float:
    return 0.5 * abs(np.sum(c[:, 0] * np.roll(c[:, 1], -1) - np.roll(c[:, 0], -1) * c[:, 1]))


def line_score(H: np.ndarray, dist: np.ndarray) -> tuple[float, int, int, int]:
    """(score, supported, samples, good lines) of court -> image homography H on a distance-to-line-pixel map.
    Every court line inside the image is sampled every STEP_PX; the per-line term keeps a court squashed onto one
    stripe from winning."""
    h, w = dist.shape
    sup = tot = good = 0
    for a, b in LINES.values():
        pts = cv2.perspectiveTransform(np.linspace(a, b, 300, dtype=np.float64).reshape(-1, 1, 2), H).reshape(-1, 2)
        pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] < w) & (pts[:, 1] >= 0) & (pts[:, 1] < h)]
        if len(pts) < 2:
            continue
        length = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        n = max(2, int(length / STEP_PX))
        p = pts[np.linspace(0, len(pts) - 1, n).astype(int)].astype(int)
        k = int((dist[p[:, 1], p[:, 0]] <= SUPPORT_PX).sum())
        sup, tot = sup + k, tot + n
        good += int(k / n >= 0.5 and length > 0.05 * w)
    return sup - 0.5 * (tot - sup) + 200.0 * good, sup, tot, good


def _scale(img: np.ndarray) -> tuple[np.ndarray, float]:
    s = WORK_WIDTH / img.shape[1]
    if abs(s - 1) < 1e-6:
        return img, 1.0
    return cv2.resize(img, (WORK_WIDTH, int(round(img.shape[0] * s))), interpolation=cv2.INTER_AREA), s


def _search(mask: np.ndarray) -> tuple[float, np.ndarray | None, tuple]:
    h, w = mask.shape
    dist = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 3)
    lines = candidates(mask)
    flat = [c for c in lines if min(c["ang"], 180 - c["ang"]) < FLAT_DEG]
    steep = [c for c in lines if min(c["ang"], 180 - c["ang"]) >= FLAT_DEG]
    best = (-np.inf, None, ())
    for sides, cross in ((steep, flat), (flat, steep)):
        for s1, s2 in itertools.combinations(sorted(sides, key=lambda c: -c["len"])[:MAX_SIDES], 2):
            for c1, c2 in itertools.combinations(sorted(cross, key=lambda c: -c["len"])[:MAX_CROSS], 2):
                q = [np.cross(s["l"], c["l"]) for c, s in ((c1, s1), (c1, s2), (c2, s2), (c2, s1))]
                if any(abs(x[2]) < 1e-9 for x in q):
                    continue
                img_pts = np.array([x[:2] / x[2] for x in q])
                if np.abs(img_pts).max() > 4 * max(w, h):
                    continue
                for xa, xb in itertools.permutations(CROSS_X, 2):
                    for ya, yb in (SIDE_Y, SIDE_Y[::-1]):
                        court = np.array([[xa, ya], [xa, yb], [xb, yb], [xb, ya]])
                        H, _ = cv2.findHomography(court, img_pts)
                        if H is None:
                            continue
                        cc = corners_from_homography(H)
                        if (
                            not court_is_plausible(cc, (w, h))
                            or _area(cc) < MIN_AREA * w * h
                            or not well_shaped(cc, w)
                            or not seen_from_a_camera(H, (w, h))
                        ):
                            continue
                        sc = line_score(H, dist)
                        if sc[0] > best[0]:
                            best = (sc[0], H, sc)
    return best


def fit(img: np.ndarray) -> Fit | None:
    """The best court fit to the painted lines of an image (bright or dark lines), or None."""
    small, s = _scale(img)
    S = np.diag([s, s, 1.0])
    out = None
    for dark in (False, True):
        score, H, sc = _search(line_pixels(small, dark=dark))
        if H is not None and (out is None or score > out.score):
            out = Fit(np.linalg.inv(S) @ H, float(score), int(sc[1]), int(sc[2]), int(sc[3]), dark)
    return out


def score_homography(img: np.ndarray, H: np.ndarray, dark: bool = False) -> Fit:
    """Line evidence for a court -> image homography found another way, on the same terms as `fit`."""
    small, s = _scale(img)
    Hs = np.diag([s, s, 1.0]) @ np.asarray(H, float)
    dist = cv2.distanceTransform(1 - line_pixels(small, dark=dark), cv2.DIST_L2, 3)
    score, sup, tot, good = line_score(Hs, dist)
    return Fit(np.asarray(H, float), float(score), sup, tot, good, dark)


NET_TOPS = (2.43, 2.24)  # men's, women's net height (m)


def pose_from_homography(H: np.ndarray, focal: float, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """(R, t) of a camera with this focal length (square pixels, centred principal point) that maps the floor by H
    (court metres -> image): K^-1 H = s [r1 r2 t], one scale s for both columns so floor points still map exactly by
    H (r1, r2 are orthonormal only at the right focal length), with the sign that puts the camera above the floor."""
    w, h = size
    K = np.array([[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1.0]])
    M = np.linalg.inv(K) @ np.asarray(H, float)
    lam = 2.0 / (np.linalg.norm(M[:, 0]) + np.linalg.norm(M[:, 1]))
    for sign in (1.0, -1.0):
        r1, r2, t = sign * lam * M[:, 0], sign * lam * M[:, 1], sign * lam * M[:, 2]
        r3 = np.cross(r1, r2)
        r3 /= np.linalg.norm(r3)
        R = np.column_stack([r1, r2, r3])
        if (-np.linalg.inv(R) @ t)[2] > 0:  # camera centre above the floor (court frame z up)
            return R, t
    return R, t


def project(H: np.ndarray, focal: float, size: tuple[int, int], points: np.ndarray) -> np.ndarray:
    """Image positions of 3D court points (n x 3) for the camera that `pose_from_homography` gives."""
    w, h = size
    R, t = pose_from_homography(H, focal, size)
    K = np.array([[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1.0]])
    p = (K @ (R @ np.asarray(points, float).T + t[:, None])).T
    return p[:, :2] / p[:, 2:3]


def focal_from_net(
    img: np.ndarray, H: np.ndarray, heights=NET_TOPS, min_band_px: float = 8.0
) -> tuple[float, float, float] | None:
    """(focal px, net height m, support) from the net tape: the white band along the top of the net, above the centre
    line. Its image position depends on the focal length, which the floor alone leaves undetermined in a symmetric
    end-line view. Searches focal lengths (0.3-5 image widths) and both net heights for the most samples of the net's
    top tape (weight 0.7) and bottom band, 1 m lower (0.3), on line pixels. The painted floor lines are removed from
    the line pixels first and the net's 1 m band must stand at least min_band_px tall, so the tape cannot be matched
    to a floor line. None when under half are supported."""
    small, s = _scale(img)
    Hs = np.diag([s, s, 1.0]) @ np.asarray(H, float)
    h, w = small.shape[:2]
    mask = line_pixels(small)
    for a, b in LINES.values():  # the floor lines are not the net
        q = cv2.perspectiveTransform(np.linspace(a, b, 300, dtype=np.float64).reshape(-1, 1, 2), Hs).reshape(-1, 2)
        cv2.polylines(mask, [q.astype(np.int32)], False, 0, 9)
    dist = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 3)
    ys = np.linspace(0.0, 9.0, 60)
    found = []
    for f in np.geomspace(0.3 * w, 5.0 * w, 240):
        for top in heights:
            q = project(Hs, f, (w, h), np.c_[np.full_like(ys, 9.0), ys, np.full_like(ys, top)])
            low = project(Hs, f, (w, h), np.array([[9.0, 4.5, top - 1.0], [9.0, 4.5, top]]))
            if np.linalg.norm(low[1] - low[0]) < min_band_px:
                continue
            qb = project(Hs, f, (w, h), np.c_[np.full_like(ys, 9.0), ys, np.full_like(ys, top - 1.0)])
            sups = []
            for line in (q, qb):  # the top tape and the bottom band of the net
                inside = (line[:, 0] >= 0) & (line[:, 0] < w) & (line[:, 1] >= 0) & (line[:, 1] < h)
                if inside.sum() < 20:
                    break
                p = line[inside].astype(int)
                sups.append(float((dist[p[:, 1], p[:, 0]] <= SUPPORT_PX).mean()))
            if len(sups) < 2:
                continue
            found.append((f / s, top, 0.7 * sups[0] + 0.3 * sups[1]))
    if not found:
        return None
    best = max(found, key=lambda x: x[2])
    if best[2] < 0.5:
        return None
    # a tape a few pixels wide supports a range of focal lengths about equally: take the middle of that range
    near = [x[0] for x in found if x[1] == best[1] and x[2] >= best[2] - 0.02]
    return float(np.median(near)), best[1], best[2]
