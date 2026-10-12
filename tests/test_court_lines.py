import cv2
import numpy as np
import pytest

from vball import court_lines
from vball.calibration import look_at
from vball.court import LINES
from vball.court_keypoints import CORNER_IDS, K6Y7R_FLOOR

SIZE = (1280, 720)
VIEWS = {
    "side": look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1100.0, SIZE),
    "end_line": look_at([-9.0, 4.5, 8.0], [8.0, 4.5, 0.0], 1000.0, SIZE),
}


def court_image(cam, line=(255, 255, 255), floor=(70, 120, 180), seed=0) -> tuple[np.ndarray, np.ndarray]:
    """A floor with painted court lines (5 cm wide) seen by `cam`, some noise and a few distracting marks; and the
    true court -> image homography."""
    rng = np.random.default_rng(seed)
    img = np.clip(np.full((SIZE[1], SIZE[0], 3), floor, float) + rng.normal(0, 6, (SIZE[1], SIZE[0], 3)), 0, 255).astype(np.uint8)
    pts = np.array([[0, 0], [18, 0], [18, 9], [0, 9]], float)
    H, _ = cv2.findHomography(pts, cam.project(np.c_[pts, np.zeros(4)]))
    for a, b in LINES.values():
        q = cv2.perspectiveTransform(np.linspace(a, b, 200).reshape(-1, 1, 2), H).reshape(-1, 2)
        cv2.polylines(img, [q.astype(np.int32)], False, line, 3, cv2.LINE_AA)
    for _ in range(6):  # logos and stray marks
        x, y = rng.integers(100, SIZE[0] - 100), rng.integers(100, SIZE[1] - 100)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(10, 40)), (int(rng.integers(0, 255)),) * 3, -1)
    return img, H


def corner_error(H_fit, H_true) -> float:
    c = K6Y7R_FLOOR[CORNER_IDS].astype(np.float64).reshape(-1, 1, 2)
    a = cv2.perspectiveTransform(c, H_fit).reshape(-1, 2)
    b = cv2.perspectiveTransform(c, H_true).reshape(-1, 2)
    # the court is symmetric: a fit rotated by 180 degrees in court coordinates is the same court
    return min(np.abs(a - b).max(), np.abs(a[[2, 3, 0, 1]] - b).max())


@pytest.mark.parametrize("view", list(VIEWS))
def test_the_court_is_found_on_white_lines(view):
    img, H = court_image(VIEWS[view])
    f = court_lines.fit(img)
    assert f is not None and not f.dark
    assert corner_error(f.H, H) < 6.0
    assert f.good_lines >= 5 and f.support > 0.8


def test_dark_lines_are_found_too():
    img, H = court_image(VIEWS["end_line"], line=(30, 30, 30), floor=(150, 170, 190))
    f = court_lines.fit(img)
    assert f is not None and f.dark and corner_error(f.H, H) < 6.0


def test_a_larger_image_gives_the_homography_in_its_own_pixels():
    img, H = court_image(VIEWS["side"])
    big = cv2.resize(img, (1920, 1080), interpolation=cv2.INTER_LINEAR)
    f = court_lines.fit(big)
    assert corner_error(f.H, np.diag([1.5, 1.5, 1.0]) @ H) < 9.0


def test_a_wrong_court_scores_lower_than_the_right_one():
    img, H = court_image(VIEWS["end_line"])
    squeezed = H @ np.array([[0.5, 0, 0], [0, 1, 0], [0, 0, 1.0]])  # the whole court in the near half
    right, wrong = court_lines.score_homography(img, H), court_lines.score_homography(img, squeezed)
    assert right.score > wrong.score and right.support > 0.8 > wrong.support


def test_fans_and_slivers_are_not_courts():
    assert court_lines.well_shaped(np.array([[400, 200], [880, 200], [1100, 600], [180, 600]], float), 1280)
    fan = np.array([[600, 300], [610, 300], [1100, 600], [180, 600]], float)  # far side shrunk to a point
    assert not court_lines.well_shaped(fan, 1280)


def test_empty_floor_gives_no_court():
    img = np.full((SIZE[1], SIZE[0], 3), 120, np.uint8)
    assert court_lines.fit(img) is None


def test_background_plate_removes_a_moving_player(tmp_path):
    img, _ = court_image(VIEWS["side"])
    path = tmp_path / "clip.mp4"
    v = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, SIZE)
    for t in range(40):
        f = img.copy()
        cv2.rectangle(f, (100 + 25 * t, 300), (160 + 25 * t, 460), (0, 0, 200), -1)
        v.write(f)
    v.release()
    plate = court_lines.background_plate(path, 0, 39, n=20)
    assert plate.shape == img.shape
    assert np.abs(plate.astype(int) - img.astype(int)).mean() < 6  # player gone (video compression aside)


def test_a_rectangle_seen_head_on_is_not_a_floor():
    wall = np.array([[40.0, 0, 300], [0, 40.0, 100], [0, 0, 1]])  # court metres -> image with no perspective
    assert not court_lines.seen_from_a_camera(wall, SIZE)
    assert not court_lines.seen_from_a_camera(np.array([[0, 40.0, 300], [40.0, 0, 100], [0.002, 0, 1]]), SIZE)
    _, H = court_image(VIEWS["side"])
    assert court_lines.seen_from_a_camera(H, SIZE)
