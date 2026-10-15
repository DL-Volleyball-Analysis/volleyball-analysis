import cv2
import numpy as np

from vball.court_keypoints import K6Y7R_FLOOR
from vball.datasets import cvat

H_TRUE = np.array([[60.0, -20.0, 300.0], [2.0, -45.0, 900.0], [0.0, -0.02, 1.0]])


def _xml(tmp_path, points, outside=(), occluded=()):
    rows = []
    for k, name in enumerate(cvat.POINT_NAMES):
        x, y = points[k]
        rows.append(
            f'<points label="{name}" source="manual" outside="{int(k in outside)}" '
            f'occluded="{int(k in occluded)}" points="{x:.2f},{y:.2f}" z_order="0"></points>'
        )
    xml = (
        '<annotations><image id="0" name="a.png" width="1920" height="1080">'
        f'<skeleton label="court" source="manual" occluded="0" z_order="0">{"".join(rows)}</skeleton>'
        '</image><image id="1" name="unlabelled.png" width="1920" height="1080"></image></annotations>'
    )
    path = tmp_path / "annotations.xml"
    path.write_text(xml)
    return path


def _true_points():
    floor = cv2.perspectiveTransform(K6Y7R_FLOOR[None].astype(np.float64), H_TRUE)[0]
    net = np.array([[900.0, 300.0], [900.0, 200.0], [950.0, 400.0], [950.0, 500.0]])
    return np.vstack([floor, net])


def test_reads_points_visibility_and_skips_unlabelled(tmp_path):
    labels = cvat.read_court_labels(_xml(tmp_path, _true_points(), outside={4}, occluded={9}))
    assert [lab.image for lab in labels] == ["a.png"]
    pts = labels[0].points
    assert pts[4, 2] == 0 and pts[9, 2] == 1 and pts[0, 2] == 2
    assert np.allclose(pts[0, :2], _true_points()[0], atol=0.01)


def test_correct_label_fits_and_passes(tmp_path):
    lab = cvat.read_court_labels(_xml(tmp_path, _true_points(), outside={4}))[0]
    _, err, n = cvat.floor_fit(lab)
    assert n == 9 and err < 0.1
    assert cvat.floor_residuals(lab)[1][0] < 0.1
    assert cvat.check(lab) == []


def test_swapped_points_are_caught(tmp_path):
    pts = _true_points()
    pts[[1, 3]] = pts[[3, 1]]  # numbering mistake
    lab = cvat.read_court_labels(_xml(tmp_path, pts))[0]
    problems = cvat.check(lab)
    assert any("k01" in p for p in problems) and any("k03" in p for p in problems)


def test_too_few_points(tmp_path):
    lab = cvat.read_court_labels(_xml(tmp_path, _true_points(), outside=set(range(3, 10))))[0]
    assert any("need 4" in p for p in cvat.check(lab))
