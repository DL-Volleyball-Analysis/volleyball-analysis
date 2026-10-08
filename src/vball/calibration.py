"""Camera calibration from court keypoints: focal length and pose in the court frame.

Model: pinhole, square pixels, principal point at the image centre, no lens distortion. Court frame
from court.py (metres, x along the 18 m length, y across, z up).

1. Floor homography from the visible floor keypoints -> initial focal length (zero-skew constraint,
   `court_keypoints.focal_from_homography`) -> initial pose with solvePnP on the floor points.
2. Refine focal length and pose together (SciPy least squares) on every visible keypoint. The net-band
   points are off the floor, which makes the problem non-planar; both net heights (men / women) are
   tried and the lower reprojection error is kept unless the caller pins one.
3. Quality gate: a median reprojection error above the threshold marks the calibration unusable, and
   no 3D trajectory is computed from it.

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


def _residuals(params: np.ndarray, obj: np.ndarray, img: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    cam = Camera(params[0], params[1:4], params[4:7], size)
    return (cam.project(obj) - img).ravel()


def _refine(f0: float, rvec: np.ndarray, tvec: np.ndarray, obj: np.ndarray, img: np.ndarray,
            size: tuple[int, int]) -> tuple[Camera, float]:
    x0 = np.concatenate([[f0], np.ravel(rvec), np.ravel(tvec)])
    sol = least_squares(_residuals, x0, args=(obj, img, size), loss="huber", f_scale=2.0)
    cam = Camera(float(sol.x[0]), sol.x[1:4], sol.x[4:7], size)
    err = float(np.median(np.linalg.norm(cam.project(obj) - img, axis=1)))
    return cam, err


def calibrate(image_points: np.ndarray, image_size: tuple[int, int], net_top: float | None = None,
              max_error_px: float | None = None) -> Calibration:
    """Calibrate one view from the 14 k6y7r keypoints.

    image_points: (14, 2) pixels, NaN rows for keypoints that are not visible.
    net_top: pin the net height (m); None tries men's and women's and keeps the lower error.
    max_error_px: quality gate; default MAX_ERROR_FRACTION of the image width.
    """
    pts = np.asarray(image_points, float)
    visible = ~np.isnan(pts).any(axis=1)
    floor = [i for i in K6Y7R_FLOOR_IDS if visible[i]]
    net = [i for i in K6Y7R_NET_IDS if visible[i]]
    gate = max_error_px if max_error_px is not None else MAX_ERROR_FRACTION * image_size[0]
    if len(floor) < 4:
        return Calibration("unusable", None, None, None, f"{len(floor)} floor keypoints (need 4)")

    floor3d = k6y7r_points_3d()[floor]
    H, _ = cv2.findHomography(floor3d[:, :2], pts[floor], 0)
    f0 = focal_from_homography(H, image_size) if H is not None else None
    if f0 is None:  # frontal view: the zero-skew constraint is degenerate; start from a normal lens
        f0 = float(max(image_size))
    K0 = np.array([[f0, 0, image_size[0] / 2], [0, f0, image_size[1] / 2], [0, 0, 1.0]])
    ok, rvec, tvec = cv2.solvePnP(floor3d, pts[floor], K0, None, flags=cv2.SOLVEPNP_IPPE)
    if not ok:
        return Calibration("unusable", None, None, None, "pose from the floor points failed")

    if net:
        heights = [net_top] if net_top is not None else [NET_TOP_MEN, NET_TOP_WOMEN]
        best = None
        for height in heights:
            ids = floor + net
            cam, err = _refine(f0, rvec, tvec, k6y7r_points_3d(height)[ids], pts[ids], image_size)
            if best is None or err < best[1]:
                best = (cam, err, height)
        cam, err, height = best
        status = "ok"
    else:
        cam, err = _refine(f0, rvec, tvec, floor3d, pts[floor], image_size)
        height, status = None, "floor_only"

    if cam.focal <= 0 or cam.position[2] <= 0:
        return Calibration("unusable", None, err, height, "camera below the floor or negative focal length")
    if err > gate:
        return Calibration("unusable", cam, err, height, f"reprojection error {err:.1f} px > {gate:.1f} px")
    return Calibration(status, cam, err, height)


def look_at(position, target, focal: float, image_size: tuple[int, int]) -> Camera:
    """Camera at `position` looking at `target` (court metres), z up. For tests and synthetic data."""
    c, t = np.asarray(position, float), np.asarray(target, float)
    fwd = (t - c) / np.linalg.norm(t - c)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.vstack([right, down, fwd])  # rows: camera x (right), y (down), z (forward) in court frame
    return Camera(focal, cv2.Rodrigues(R)[0].ravel(), -R @ c, image_size)
