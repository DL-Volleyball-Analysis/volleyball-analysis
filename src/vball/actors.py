"""Who performs the action: per-player action scores, combined over frames and with the ball's position.

The action model boxes the acting player in a single frame, so it also fires on players who only look like
they set or spike (a blocker's raised arms, a teammate running in). In volleyball the player who sets, spikes,
receives or blocks is the one at the ball. Each player's action score is therefore weighted by a prior on the
distance between the ball and the player's box:

    prior = exp(-(d / (k * h))^2),  d = distance from the ball to the box (0 inside), h = box height
    score' = score * (floor + (1 - floor) * prior)

`floor` keeps some evidence when the ball is far or unknown (missed detections, a block before the touch). With
no ball at all the scores are unchanged. Scores over several frames of one player are combined by their mean
of the top `top_n` frames, so a single noisy frame neither creates nor erases an action.

    s = player_scores(detections, boxes, ball=ball_per_frame)   # {player: (frames, actions)}, ball-weighted
    s = combine(s, top_n=3)                                     # {player: (actions,)}
    labels = decide(s, threshold)                               # {player: action or None}
    (with_ball weights already combined scores with one ball position)
"""
from dataclasses import dataclass

import numpy as np

from .actions import ACTIONS, iou


@dataclass(frozen=True)
class ActorConfig:
    min_iou: float = 0.3     # action box vs player box
    top_n: int = 3           # frames averaged per player
    k: float = 1.0           # prior width, in box heights
    floor: float = 0.3       # prior never below this (ball far or missed)
    threshold: float = 0.4   # combined score needed for an action


def player_scores(detections: dict[int, np.ndarray], boxes: dict[int, dict[int, np.ndarray]],
                  cfg: ActorConfig = ActorConfig(), ball: dict[int, np.ndarray | None] | None = None,
                  n_actions: int = len(ACTIONS)) -> dict[int, np.ndarray]:
    """detections: frame -> rows of (action index, conf, x1, y1, x2, y2); boxes: frame -> {player: (x1, y1, x2, y2)};
    ball: frame -> (x, y) or None (optional). Per player: (frames, actions) best confidence of each action among
    the detections overlapping its box, weighted by the ball prior of that frame when a ball is given."""
    out: dict[int, list[np.ndarray]] = {}
    for f, players in boxes.items():
        det = np.asarray(detections.get(f, np.zeros((0, 6))), float).reshape(-1, 6)
        ids = list(players)
        P = np.array([players[p] for p in ids], float).reshape(-1, 4)
        rows = {p: np.zeros(n_actions) for p in ids}
        for a, conf, *box in det:
            if not len(ids):
                break
            o = iou(np.array(box), P)
            k = int(np.argmax(o))
            if o[k] >= cfg.min_iou:
                r = rows[ids[k]]
                r[int(a)] = max(r[int(a)], conf)
        xy = None if ball is None else ball.get(f)
        for p in ids:
            w = ball_prior(P[ids.index(p)], xy, cfg) if xy is not None else 1.0
            out.setdefault(p, []).append(rows[p] * w)
    return {p: np.stack(v) for p, v in out.items()}


def combine(scores: dict[int, np.ndarray], top_n: int = ActorConfig().top_n) -> dict[int, np.ndarray]:
    """Per player and action: mean of the `top_n` highest frame scores (fewer frames: mean of those)."""
    return {p: np.sort(s, axis=0)[::-1][:top_n].mean(axis=0) for p, s in scores.items()}


def box_distance(box: np.ndarray, xy: np.ndarray) -> float:
    """Distance from a point to a box (0 inside)."""
    x1, y1, x2, y2 = box
    dx = max(x1 - xy[0], 0.0, xy[0] - x2)
    dy = max(y1 - xy[1], 0.0, xy[1] - y2)
    return float(np.hypot(dx, dy))


def ball_prior(box: np.ndarray, xy: np.ndarray | None, cfg: ActorConfig = ActorConfig()) -> float:
    if xy is None or np.isnan(xy).any():
        return 1.0
    h = max(float(box[3] - box[1]), 1.0)
    p = np.exp(-(box_distance(box, xy) / (cfg.k * h)) ** 2)
    return float(cfg.floor + (1 - cfg.floor) * p)


def with_ball(scores: dict[int, np.ndarray], boxes: dict[int, np.ndarray], ball_xy: np.ndarray | None,
              cfg: ActorConfig = ActorConfig()) -> dict[int, np.ndarray]:
    """Scores weighted by each player's prior at the ball (players without a box keep their scores)."""
    return {p: s * (ball_prior(np.asarray(boxes[p], float), ball_xy, cfg) if p in boxes else 1.0)
            for p, s in scores.items()}


def decide(scores: dict[int, np.ndarray], threshold: float = ActorConfig().threshold) -> dict[int, int | None]:
    """Per player: the index of its best action if its score reaches the threshold, else None."""
    return {p: (int(np.argmax(s)) if s.max() >= threshold else None) for p, s in scores.items()}
