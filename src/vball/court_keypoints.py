"""Court keypoint definitions for the learned court detector.

Court frame from court.py (metres, x along the 18 m length, net at x = 9) plus z up.
With z up the frame is right-handed only if the "y = WIDTH" sideline is the one the
labels number 0..4; this was checked on the dataset (single-view calibration puts the
camera above the floor, ~4.6 m median).

volleyballcourt/volleyball-court-keypoints-k6y7r (Roboflow, CC BY 4.0), 14 points, full court.
The numbering is image-based (checked on all 495 labels): 0-4 run along the FAR sideline from
left to right in the image (308/334, 148/149), 5-9 along the near sideline back from right to left:
  0-4   far sideline: end line -> attack line -> centre -> attack line -> other end line
  5-9   near sideline, starting below point 4 (so 0, 4, 5, 9 are the corners in polygon order)
  10/11 net bottom / top band above point 2 (far sideline, at the antenna)
  12/13 net top / bottom band above point 7 (near sideline)
primaryws/volleyball_court_keypoints_regression_dataset v7 (CC BY 4.0), 4 points: the front-zone
corners (attack line x sideline), same handedness, = k6y7r points 1, 3, 6, 8 (VNL4_TO_K6Y7R).
Only 5 VNL broadcast clips from one camera, so it is used as an external test set, not for training.

Verified on the labels: floor points map to 0 / 6 / 9 / 12 / 18 m within ~0.05 m (median,
homography from the corners); net points sit on the vertical through points 2 / 7 and come out
at ~1.42 m and ~2.40 m (net top is 2.43 m men / 2.24 m women, bottom band 1 m lower).
"""
import cv2
import numpy as np

from .court import ATTACK_LINE_OFFSET, LENGTH, NET_X, WIDTH

NET_TOP_MEN, NET_TOP_WOMEN = 2.43, 2.24
NET_BAND_HEIGHT = 1.0

_A, _B = NET_X - ATTACK_LINE_OFFSET, NET_X + ATTACK_LINE_OFFSET
K6Y7R_FLOOR = np.float32([
    [0, WIDTH], [_A, WIDTH], [NET_X, WIDTH], [_B, WIDTH], [LENGTH, WIDTH],
    [LENGTH, 0], [_B, 0], [NET_X, 0], [_A, 0], [0, 0],
])
K6Y7R_FLOOR_IDS = list(range(10))
K6Y7R_NET_IDS = [10, 11, 12, 13]
# Index permutation for a horizontal image flip. The numbering is image-based, so a mirror keeps
# far as far and reverses left/right: 0<->4, 1<->3, 5<->9, 6<->8; net points stay. Checked on the
# labels: mirrored + permuted labels keep every annotation rule (far sideline, left-to-right order,
# net above point 2) in >= 333/334 images. (The dataset's data.yaml ships the identity: wrong.)
K6Y7R_FLIP_IDX = [4, 3, 2, 1, 0, 9, 8, 7, 6, 5, 10, 11, 12, 13]

VNL4_TO_K6Y7R = [1, 3, 6, 8]


def k6y7r_points_3d(net_top: float = NET_TOP_MEN) -> np.ndarray:
    """All 14 keypoints in court metres (x, y, z), for PnP / 3D calibration."""
    lo = net_top - NET_BAND_HEIGHT
    net = [[NET_X, WIDTH, lo], [NET_X, WIDTH, net_top], [NET_X, 0, net_top], [NET_X, 0, lo]]
    floor = np.hstack([K6Y7R_FLOOR, np.zeros((10, 1), np.float32)])
    return np.vstack([floor, np.float32(net)])


FRONT_ZONE_IDS = VNL4_TO_K6Y7R  # attack line x sideline: the four points the VNL set labels


def complete_floor(image_pts: np.ndarray, ids: list[int]) -> np.ndarray:
    """All 10 floor keypoints in image pixels from at least 4 known ones (exact for a pinhole camera:
    the floor is a plane, so its image is a homography of the court)."""
    H, _ = cv2.findHomography(K6Y7R_FLOOR[ids].astype(np.float64), np.float64(image_pts), 0)
    if H is None:
        raise ValueError("degenerate floor points")
    return cv2.perspectiveTransform(K6Y7R_FLOOR.reshape(-1, 1, 2).astype(np.float64), H).reshape(-1, 2)


def focal_from_homography(H: np.ndarray, image_size: tuple[int, int]) -> float | None:
    """Focal length (pixels) from a court -> image homography, assuming square pixels and the
    principal point at the image centre (zero-skew constraint). None when the view is too frontal."""
    w, h = image_size
    T = np.array([[1, 0, -w / 2], [0, 1, -h / 2], [0, 0, 1]])
    G = T @ H
    denom = G[2, 0] * G[2, 1]
    if abs(denom) < 1e-12:
        return None
    f2 = -(G[0, 0] * G[0, 1] + G[1, 0] * G[1, 1]) / denom
    return float(np.sqrt(f2)) if f2 > 0 else None


def net_points_from_floor(floor_img: np.ndarray, image_size: tuple[int, int],
                          net_top: float = NET_TOP_MEN) -> np.ndarray | None:
    """Image positions of the 4 net-band points (ids 10-13) from the 10 floor points of one frame:
    focal length from the floor homography, camera pose from the floor points, then projection."""
    H, _ = cv2.findHomography(K6Y7R_FLOOR.astype(np.float64), np.float64(floor_img), 0)
    f = focal_from_homography(H, image_size) if H is not None else None
    if f is None:
        return None
    w, h = image_size
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]])
    obj = np.hstack([K6Y7R_FLOOR, np.zeros((10, 1), np.float32)]).astype(np.float64)
    ok, rvec, tvec = cv2.solvePnP(obj, np.float64(floor_img), K, None, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    net3d = k6y7r_points_3d(net_top)[K6Y7R_NET_IDS].astype(np.float64)
    return cv2.projectPoints(net3d, rvec, tvec, K, None)[0].reshape(-1, 2)
