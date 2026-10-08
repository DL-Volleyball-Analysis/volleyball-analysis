import cv2
import numpy as np

from vball.court_keypoints import K6Y7R_FLIP_IDX, K6Y7R_FLOOR


def project_side_view(width=1280):
    """Image positions of the 10 floor points for a camera behind the near sideline (side view).
    Court y = 9 is the far sideline; x grows left to right in the image."""
    img = np.float32([[300, 250], [980, 250], [1200, 600], [80, 600]])   # far-left, far-right, near-right, near-left
    court = np.float32([[0, 9], [18, 9], [18, 0], [0, 0]])
    H = cv2.getPerspectiveTransform(court, img)
    return cv2.perspectiveTransform(K6Y7R_FLOOR.reshape(-1, 1, 2), H).reshape(-1, 2), width


def labelling_rules(pts):
    far = pts[0:5, 1].mean() < pts[5:10, 1].mean()
    left_to_right = all(np.diff(pts[0:5, 0]) > 0)
    near_back = all(np.diff(pts[5:10, 0]) < 0)
    return far, left_to_right, near_back


def test_layout_follows_the_image_rule():
    pts, _ = project_side_view()
    assert labelling_rules(pts) == (True, True, True)


def test_flip_idx_keeps_the_rule_after_a_mirror():
    pts, w = project_side_view()
    mirrored = pts.copy()
    mirrored[:, 0] = w - mirrored[:, 0]
    relabelled = mirrored[K6Y7R_FLIP_IDX[:10]]
    assert labelling_rules(relabelled) == (True, True, True)


def test_flip_idx_is_an_involution_and_keeps_net_points():
    idx = np.array(K6Y7R_FLIP_IDX)
    assert (idx[idx] == np.arange(14)).all()
    assert list(idx[10:]) == [10, 11, 12, 13]


def synthetic_camera(f=1400.0, size=(1920, 1080), eye=(5.0, -14.0, 9.0)):
    """A broadcast-like camera beside and above the court (z up), looking at the court centre.
    The default eye is off the centre line: a perfectly centred camera has no vanishing point along
    the court's length, and its focal length cannot be recovered from the floor alone."""
    w, h = size
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]])
    eye, target = np.array(eye, float), np.array([9.0, 4.5, 0.0])
    z = target - eye; z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z])
    tvec = -R @ eye
    rvec, _ = cv2.Rodrigues(R)
    return K, rvec, tvec, size


def project(pts3d, cam):
    K, rvec, tvec, _ = cam
    return cv2.projectPoints(np.float64(pts3d), rvec, tvec, K, None)[0].reshape(-1, 2)


def test_complete_floor_from_front_zone_is_exact():
    from vball.court_keypoints import FRONT_ZONE_IDS, complete_floor, k6y7r_points_3d
    cam = synthetic_camera()
    truth = project(k6y7r_points_3d()[:10], cam)
    completed = complete_floor(truth[FRONT_ZONE_IDS], FRONT_ZONE_IDS)
    assert np.abs(completed - truth).max() < 1e-3  # pixels; float32 court coordinates


def test_net_points_from_floor_recover_the_camera():
    from vball.court_keypoints import K6Y7R_NET_IDS, k6y7r_points_3d, net_points_from_floor
    cam = synthetic_camera()
    pts = k6y7r_points_3d()
    net = net_points_from_floor(project(pts[:10], cam), cam[3])
    assert net is not None
    assert np.abs(net - project(pts[K6Y7R_NET_IDS], cam)).max() < 0.5  # pixels


def test_centred_camera_gives_no_net_points_instead_of_a_guess():
    from vball.court_keypoints import k6y7r_points_3d, net_points_from_floor
    cam = synthetic_camera(eye=(9.0, -14.0, 9.0))
    assert net_points_from_floor(project(k6y7r_points_3d()[:10], cam), cam[3]) is None
