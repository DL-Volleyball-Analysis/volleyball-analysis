"""Indoor volleyball court model and homography helpers.

Court coordinates are metres: x along the 18 m length (net / centre line at x = 9),
y along the 9 m width. A homography H maps court (x, y) -> image (u, v).
"""
import cv2
import numpy as np

LENGTH, WIDTH = 18.0, 9.0
NET_X = 9.0
ATTACK_LINE_OFFSET = 3.0

LINES = {
    "sideline_a": ((0, 0), (LENGTH, 0)),
    "sideline_b": ((0, WIDTH), (LENGTH, WIDTH)),
    "endline_a": ((0, 0), (0, WIDTH)),
    "endline_b": ((LENGTH, 0), (LENGTH, WIDTH)),
    "centre": ((NET_X, 0), (NET_X, WIDTH)),
    "attack_a": ((NET_X - ATTACK_LINE_OFFSET, 0), (NET_X - ATTACK_LINE_OFFSET, WIDTH)),
    "attack_b": ((NET_X + ATTACK_LINE_OFFSET, 0), (NET_X + ATTACK_LINE_OFFSET, WIDTH)),
}
CORNERS = np.float32([[0, 0], [LENGTH, 0], [LENGTH, WIDTH], [0, WIDTH]])


def to_image(H, pts) -> np.ndarray:
    return cv2.perspectiveTransform(np.float32(pts).reshape(-1, 1, 2), np.asarray(H, np.float64)).reshape(-1, 2)


def to_court(H, pts) -> np.ndarray:
    return to_image(np.linalg.inv(np.asarray(H, np.float64)), pts)


def side_of_net(x_m: float) -> str:
    return "a" if x_m < NET_X else "b"


def is_in(x_m: float, y_m: float, margin_m: float = 0.0) -> bool:
    """Ball landing in/out; lines are part of the court, so allow a small margin."""
    return -margin_m <= x_m <= LENGTH + margin_m and -margin_m <= y_m <= WIDTH + margin_m


def draw(img, H, color=(0, 255, 255), thickness=3):
    out = img.copy()
    for a, b in LINES.values():
        q = to_image(H, np.linspace(a, b, 80)).astype(np.int32)
        cv2.polylines(out, [q], False, color, thickness)
    return out
