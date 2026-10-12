import numpy as np

from vball.actions import ACTIONS
from vball.actors import (
    ActorConfig,
    ball_prior,
    box_distance,
    classifier_rows,
    combine,
    decide,
    person_crop,
    player_scores,
)

SET, SPIKE = ACTIONS.index("set"), ACTIONS.index("spike")


def test_detections_go_to_the_overlapping_player():
    boxes = {0: {1: np.array([0, 0, 10, 20]), 2: np.array([100, 0, 110, 20])}}
    det = {0: np.array([[SET, 0.8, 1, 1, 10, 20], [SPIKE, 0.5, 300, 0, 310, 20]])}  # the spike overlaps nobody
    s = player_scores(det, boxes)
    assert s[1][0, SET] == 0.8 and s[1][0].sum() == 0.8 and s[2].sum() == 0


def test_combine_uses_the_top_frames():
    s = {1: np.array([[0.9, 0], [0.8, 0], [0.7, 0], [0.0, 0.95]])}
    c = combine(s, top_n=3)
    assert np.isclose(c[1][0], 0.8) and np.isclose(c[1][1], 0.95 / 3)


def test_ball_prior_favours_the_player_at_the_ball():
    near, far = np.array([0, 0, 10, 40]), np.array([200, 0, 210, 40])
    ball = np.array([12.0, 5.0])
    assert box_distance(near, np.array([5.0, 5.0])) == 0 and np.isclose(box_distance(near, ball), 2.0)
    cfg = ActorConfig(k=1.0, floor=0.3)
    assert ball_prior(near, ball, cfg) > 0.99 and np.isclose(ball_prior(far, ball, cfg), 0.3, atol=1e-6)
    assert ball_prior(far, None, cfg) == 1.0 and ball_prior(far, np.array([np.nan, np.nan]), cfg) == 1.0


def test_the_ball_turns_a_look_alike_into_no_action():
    # two players both look like setting; only the one at the ball keeps it
    scores = {1: np.eye(len(ACTIONS))[SET] * 0.7, 2: np.eye(len(ACTIONS))[SET] * 0.7}
    boxes = {1: np.array([0, 0, 10, 40]), 2: np.array([300, 0, 310, 40])}
    def weighted(ball, cfg=ActorConfig()):
        return {p: sc * ball_prior(boxes[p], ball, cfg) for p, sc in scores.items()}
    assert decide(weighted(np.array([5.0, -2.0]), ActorConfig(floor=0.3)), threshold=0.4) == {1: SET, 2: None}
    assert decide(weighted(None), threshold=0.4) == {1: SET, 2: SET}


def test_per_frame_ball_weighting():
    boxes = {0: {1: np.array([0, 0, 10, 40]), 2: np.array([300, 0, 310, 40])},
             1: {1: np.array([0, 0, 10, 40]), 2: np.array([300, 0, 310, 40])}}
    det = {0: np.array([[SET, 0.8, 300, 0, 310, 40]]), 1: np.array([[SET, 0.8, 0, 0, 10, 40]])}
    ball = {0: np.array([5.0, 5.0]), 1: None}   # frame 0: the ball is at player 1, not at the "setter" 2
    s = player_scores(det, boxes, ActorConfig(floor=0.25), ball=ball)
    assert np.isclose(s[2][0, SET], 0.8 * 0.25, atol=1e-6) and np.isclose(s[1][1, SET], 0.8)


def test_person_crop_is_clipped_and_square():
    img = np.full((100, 100, 3), 255, np.uint8)
    c = person_crop(img, (90, 90, 120, 130), 0.1)  # widened to (87, 86), clipped at 100: 13 x 14, padded to 14 x 14
    assert c.shape == (14, 14, 3) and (c[:, -1] == 114).all() and (c[:, 0] == 255).all()  # odd padding goes right
    assert person_crop(img, (200, 200, 210, 210), 0.1) is None
    tall = person_crop(np.full((200, 200, 3), 255, np.uint8), (50, 20, 70, 100), 0.0)
    assert tall.shape == (80, 80, 3) and (tall[:, 30:50] == 255).all() and (tall[:, :30] == 114).all()


NAMES = ["blocking", "digging", "falling", "jumping", "moving", "setting", "spiking", "standing", "waiting"]


def test_classifier_rows_keep_our_actions_weighted_by_the_ball():
    boxes = np.array([[0, 0, 10, 40], [300, 0, 310, 40], [500, 0, 510, 40]])
    probs = np.zeros((3, 9))
    probs[0, NAMES.index("setting")] = 0.9    # the setter, at the ball
    probs[1, NAMES.index("setting")] = 0.9    # looks like setting, far from the ball
    probs[2, NAMES.index("standing")] = 0.95  # no action
    rows = classifier_rows(7, boxes, probs, NAMES, np.array([5.0, -2.0]), ActorConfig(k=1.0, floor=0.2), min_conf=0.25)
    assert [(r[0], r[1]) for r in rows] == [(7, "set")] and np.isclose(rows[0][2], 0.9, atol=0.02)
    assert len(classifier_rows(7, boxes, probs, NAMES, None)) == 2  # without a ball both look-alikes stay
