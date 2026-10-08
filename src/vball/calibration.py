"""Camera calibration from court keypoints: focal length and pose in the court frame.

Model: pinhole, square pixels, principal point at the image centre, no lens distortion. Court frame
from court.py (metres, x along the 18 m length, y across, z up).

1. Floor homography from the visible floor keypoints -> initial focal length (zero-skew constraint,
   `court_keypoints.focal_from_homography`) -> initial pose with solvePnP on the floor points.
2. Refine focal length and pose together (SciPy least squares) on every visible keypoint. The net-band
   points are off the floor, which makes the problem non-planar; both net heights (men / women) are
   tried and the lower reprojection error is kept unless the caller pins one.
3. Quality gates: a median reprojection error above the threshold, or a focal length the keypoints do
   not pin down (relative sd from the Jacobian), marks the calibration unusable, and no 3D trajectory
   is computed from it. A small error alone is not enough: one sideline plus the net seen head-on fits
   any zoom / distance pair equally well.

Statuses: "ok" (net points used), "floor_only" (floor points only: the focal length then rests on the
centred-principal-point assumption alone), "unusable" (too few points or error above the gate).
"""
from dataclasses import dataclass

import cv2
import numpy as np
from scipy.optimize import least_squares

from .court_keypoints import (K6Y7R_FLOOR_IDS, K6Y7R_NET_IDS, NET_TOP_MEN, NET_TOP_WOMEN,
                              focal_from_homography, k6y7r_points_3d)

MAX_ERROR_FRACTION = 0.005  # default gate: median reprojection error <= 0.5% of the image width
MAX_FOCAL_SD = 0.05         # default gate: focal length known to 5% (1 sd)


@dataclass
class Camera:
    focal: float                 # pixels
    rvec: np.ndarray             # Rodrigues rotation, court -> camera
    tvec: np.ndarray             # translation, court -> camera
    image_size: tuple[int, int]  # (width, height)

    @property
    def K(self) -> np.ndarray:
        w, h = self.image_size
        return np.array([[self.focal, 0, w / 2], [0, self.focal, h / 2], [0, 0, 1.0]])

    @property
    def R(self) -> np.ndarray:
        return cv2.Rodrigues(np.asarray(self.rvec, float))[0]

    @property
    def position(self) -> np.ndarray:
        """Camera centre in court metres."""
        return -self.R.T @ np.asarray(self.tvec, float).ravel()

    def project(self, points: np.ndarray) -> np.ndarray:
        """Court points (N, 3) in metres -> image pixels (N, 2)."""
        cam = np.asarray(points, float) @ self.R.T + np.asarray(self.tvec, float).ravel()
        uv = cam[:, :2] / cam[:, 2:3]
        w, h = self.image_size
        return uv * self.focal + np.array([w / 2, h / 2])

    def ray(self, uv: np.ndarray) -> np.ndarray:
        """Unit direction (court frame) of the ray through image point uv."""
        w, h = self.image_size
        d = np.array([(uv[0] - w / 2) / self.focal, (uv[1] - h / 2) / self.focal, 1.0])
        d = self.R.T @ d
        return d / np.linalg.norm(d)


@dataclass
class Calibration:
    status: str                    # "ok" | "floor_only" | "unusable"
    camera: Camera | None
    reprojection_px: float | None  # median over the visible keypoints
    net_top: float | None          # net height used (None for floor_only / unusable)
    reason: str = ""
    focal_sd: float | None = None  # relative sd of the focal length (from the Jacobian)


def _residuals(params: np.ndarray, obj: np.ndarray, img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    cam = Camera(params[0], params[1:4], params[4:7], size)
    return (cam.project(obj) - img).ravel()


def _refine(f0: float, rvec: np.ndarray, tvec: np.ndarray, obj: np.ndarray, img: np.ndarray,
            size: tuple[int, int]) -> tuple[Camera, float, float]:
    """Refined camera, median reprojection error (px), relative sd of the focal length.

    The focal sd comes from the Jacobian with a noise level of at least 1 px: a perfect fit can still
    leave the focal length undetermined (e.g. all points in one plane seen head-on, where zooming in
    and moving closer look the same)."""
    x0 = np.concatenate([[f0], np.ravel(rvec), np.ravel(tvec)])
    sol = least_squares(_residuals, x0, args=(obj, img, size), loss="huber", f_scale=2.0)
    cam = Camera(float(sol.x[0]), sol.x[1:4], sol.x[4:7], size)
    res = np.linalg.norm(cam.project(obj) - img, axis=1)
    err = float(np.median(res))
    sigma = max(1.0, 1.4826 * err)
    cov = sigma ** 2 * np.linalg.pinv(sol.jac.T @ sol.jac)
    focal_sd = float(np.sqrt(max(cov[0, 0], 0.0)) / abs(cam.focal))
    return cam, err, focal_sd


def _k(f: float, size: tuple[int, int]) -> np.ndarray:
    return np.array([[f, 0, size[0] / 2], [0, f, size[1] / 2], [0, 0, 1.0]])


def _floor_start(floor3d: np.ndarray, img: np.ndarray, size: tuple[int, int]):
    """(focal, rvec, tvec) from the floor homography, or None when the floor points are degenerate."""
    if np.linalg.matrix_rank(floor3d[:, :2] - floor3d[:, :2].mean(axis=0), tol=1e-6) < 2:
        return None  # all on one line
    H, _ = cv2.findHomography(floor3d[:, :2], img, 0)
    if H is None:
        return None
    f0 = focal_from_homography(H, size)
    if f0 is None:  # frontal view: the zero-skew constraint is degenerate; start from a normal lens
        f0 = float(max(size))
    ok, rvec, tvec = cv2.solvePnP(floor3d, img, _k(f0, size), None, flags=cv2.SOLVEPNP_IPPE)
    if not ok or not (np.isfinite(rvec).all() and np.isfinite(tvec).all()):
        return None
    return f0, rvec, tvec


def _focal_sweep_starts(obj: np.ndarray, img: np.ndarray, size: tuple[int, int]) -> list:
    """Poses from SQPnP for focal lengths from wide to long lens (0.5 to 4 image widths)."""
    starts = []
    for f in size[0] * np.geomspace(0.5, 4.0, 7):
        ok, rvec, tvec = cv2.solvePnP(obj, img, _k(f, size), None, flags=cv2.SOLVEPNP_SQPNP)
        if ok and np.isfinite(rvec).all() and np.isfinite(tvec).all():
            starts.append((float(f), rvec, tvec))
    return starts


def calibrate(image_points: np.ndarray, image_size: tuple[int, int], net_top: float | None = None,
              max_error_px: float | None = None, max_focal_sd: float = MAX_FOCAL_SD) -> Calibration:
    """Calibrate one view from the 14 k6y7r keypoints.

    image_points: (14, 2) pixels, NaN rows for keypoints that are not visible.
    net_top: pin the net height (m); None tries men's and women's and keeps the lower error.
    max_error_px: quality gate; default MAX_ERROR_FRACTION of the image width.
    max_focal_sd: second gate: relative sd of the focal length (catches fits that are exact but
    ambiguous, e.g. one sideline seen head-on).
    """
    pts = np.asarray(image_points, float)
    visible = ~np.isnan(pts).any(axis=1)
    floor = [i for i in K6Y7R_FLOOR_IDS if visible[i]]
    net = [i for i in K6Y7R_NET_IDS if visible[i]]
    gate = max_error_px if max_error_px is not None else MAX_ERROR_FRACTION * image_size[0]
    if len(floor) < 4:
        return Calibration("unusable", None, None, None, f"{len(floor)} floor keypoints (need 4)")

    floor3d = k6y7r_points_3d()[floor]
    floor_init = _floor_start(floor3d, pts[floor], image_size)
    if not net:
        if floor_init is None:
            return Calibration("unusable", None, None, None, "floor points on one line and no net point")
        cam, err, focal_sd = _refine(*floor_init, floor3d, pts[floor], image_size)
        height, status = None, "floor_only"
    else:
        heights = [net_top] if net_top is not None else [NET_TOP_MEN, NET_TOP_WOMEN]
        ids = floor + net
        best = None
        for height in heights:
            obj = k6y7r_points_3d(height)[ids]
            # floor homography start when the floor points allow it; otherwise (e.g. only one sideline
            # visible, so the floor points are collinear) poses for a range of focal lengths
            starts = [floor_init] if floor_init is not None else _focal_sweep_starts(obj, pts[ids], image_size)
            for start in starts:
                cam, err, focal_sd = _refine(*start, obj, pts[ids], image_size)
                if best is None or err < best[1]:
                    best = (cam, err, height, focal_sd)
        if best is None:
            return Calibration("unusable", None, None, None, "no camera pose fits the keypoints")
        cam, err, height, focal_sd = best
        status = "ok"

    if cam.focal <= 0 or cam.position[2] <= 0:
        return Calibration("unusable", None, err, height, "camera below the floor or negative focal length")
    if err > gate:
        return Calibration("unusable", cam, err, height, f"reprojection error {err:.1f} px > {gate:.1f} px",
                           focal_sd)
    if focal_sd > max_focal_sd:
        return Calibration("unusable", cam, err, height,
                           f"focal length poorly constrained (sd {100 * focal_sd:.0f}%)", focal_sd)
    return Calibration(status, cam, err, height, focal_sd=focal_sd)


def look_at(position, target, focal: float, image_size: tuple[int, int]) -> Camera:
    """Camera at `position` looking at `target` (court metres), z up. For tests and synthetic data."""
    c, t = np.asarray(position, float), np.asarray(target, float)
    fwd = (t - c) / np.linalg.norm(t - c)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.vstack([right, down, fwd])  # rows: camera x (right), y (down), z (forward) in court frame
    return Camera(focal, cv2.Rodrigues(R)[0].ravel(), -R @ c, image_size)
