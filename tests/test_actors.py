import numpy as np

from vball.actions import ACTIONS
from vball.actors import ActorConfig, ball_prior, box_distance, combine, decide, player_scores, with_ball

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
    out = decide(with_ball(scores, boxes, np.array([5.0, -2.0]), ActorConfig(floor=0.3)), threshold=0.4)
    assert out == {1: SET, 2: None}
    assert decide(with_ball(scores, boxes, None), threshold=0.4) == {1: SET, 2: SET}


def test_per_frame_ball_weighting():
    boxes = {0: {1: np.array([0, 0, 10, 40]), 2: np.array([300, 0, 310, 40])},
             1: {1: np.array([0, 0, 10, 40]), 2: np.array([300, 0, 310, 40])}}
    det = {0: np.array([[SET, 0.8, 300, 0, 310, 40]]), 1: np.array([[SET, 0.8, 0, 0, 10, 40]])}
    ball = {0: np.array([5.0, 5.0]), 1: None}   # frame 0: the ball is at player 1, not at the "setter" 2
    s = player_scores(det, boxes, ActorConfig(floor=0.25), ball=ball)
    assert np.isclose(s[2][0, SET], 0.8 * 0.25, atol=1e-6) and np.isclose(s[1][1, SET], 0.8)
