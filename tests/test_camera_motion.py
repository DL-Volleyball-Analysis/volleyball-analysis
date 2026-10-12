import cv2
import numpy as np

from vball import camera_motion


def scene(seed: int = 0, size=(1600, 900)) -> np.ndarray:
    """A textured background bigger than the view, so a pan stays inside it."""
    rng = np.random.default_rng(seed)
    img = cv2.GaussianBlur(rng.integers(0, 255, (size[1], size[0]), np.uint8), (0, 0), 2)
    for _ in range(300):
        x, y = rng.integers(0, size[0]), rng.integers(0, size[1])
        cv2.circle(img, (int(x), int(y)), int(rng.integers(3, 12)), int(rng.integers(0, 255)), -1)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def views(world: np.ndarray, homs: list[np.ndarray], size=(960, 540)) -> list[np.ndarray]:
    return [cv2.warpPerspective(world, H, size) for H in homs]


def pan(t: float) -> np.ndarray:
    """World -> view: translate left over time and zoom in a little."""
    z = 1.0 + 0.002 * t
    return np.array([[z, 0, -100 - 4.0 * t], [0, z, -80 - 0.5 * t], [0, 0, 1]])


def test_pan_is_followed():
    world = scene()
    homs = [pan(t) for t in range(40)]
    m = camera_motion.Motion(camera_motion.estimate(views(world, homs))[0])
    truth = homs[39] @ np.linalg.inv(homs[0])
    pts = np.array([[100.0, 100.0], [800.0, 120.0], [480.0, 400.0]])
    want = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), truth).reshape(-1, 2)
    assert np.abs(m.warp(0, 39, pts) - want).max() < 1.5
    assert np.abs(m.warp(39, 0, want) - pts).max() < 1.5  # and back


def test_still_camera_with_a_moving_object_stays_still():
    world = scene(1)
    frames = []
    for t in range(30):
        f = views(world, [pan(0)])[0].copy()
        cv2.rectangle(f, (100 + 12 * t, 200), (220 + 12 * t, 420), (255, 255, 255), -1)  # a "player" crossing
        frames.append(f)
    steps, share = camera_motion.estimate(frames)
    m = camera_motion.Motion(steps)
    pts = np.array([[50.0, 50.0], [900.0, 500.0]])
    assert np.abs(m.warp(0, 29, pts) - pts).max() < 1.0
    assert share[1:].min() > 0.5


def test_save_load_and_between(tmp_path):
    steps = np.stack([np.eye(3)] + [np.array([[1, 0, 2.0], [0, 1, 0], [0, 0, 1]])] * 4)
    camera_motion.save(tmp_path / "m.npz", steps, np.ones(5))
    m = camera_motion.load(tmp_path / "m.npz")
    assert np.allclose(m.warp(1, 4, [[0, 0]]), [[6, 0]])
    assert np.allclose(m.between(4, 1) @ m.between(1, 4), np.eye(3))
    assert np.allclose(m.between(0, 99), m.between(0, 4))  # clipped to the video
    assert camera_motion.load(tmp_path / "missing.npz") is None
