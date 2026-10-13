"""Who sets, spikes, receives or blocks: the action model with and without the ball, on the Volleyball dataset.

Data: the Volleyball dataset (Ibrahim et al., CVPR 2016) with per-player boxes and action labels on 9 frames
around each clip's key frame (`annot_all.pkl` of the Kaggle copy), and the ball position in every frame
(Perez et al., Pattern Recognition 2022). Label mapping to our classes: setting -> set, digging -> receive,
spiking -> spike, blocking -> block; every other player (standing, moving, waiting, jumping, falling) has no
action. Serves are not labelled in this dataset, so `serve` predictions count as wrong.

Protocol: parameters are chosen on the validation matches and reported once on the test matches.
Methods (an ablation of vball.actors):
  key frame          the action model on the key frame only
  9 frames           each player's scores combined over the 9 frames (mean of the top_n)
  + ball (labelled)  each frame weighted by the distance from the player to the labelled ball
  + ball (detected)  the same with the ball from our tracker (--ball-preds, test matches only)
Metric: per player, F1 of each action class and their macro mean.

  python scripts/eval_actions_volleyball.py detect --videos <dir> --pkl annot_all.pkl --out dets.json
  python scripts/eval_actions_volleyball.py evaluate --pkl annot_all.pkl --ann <ball annotations> \
      --dets dets.json [--ball-preds <ball eval csv.gz>]
  python scripts/eval_actions_volleyball.py classifier --pkl annot_all.pkl --ann <ball annotations> \
      --probs person_action_test_probs.csv --k 2.0 --floor 0.6
The `classifier` command scores the per-player classifier (notebooks/train_person_actions.ipynb) on the same test
players and classes, alone and with the ball prior (k and floor as chosen on validation by `evaluate`).
"""

import argparse

from vball.evaluation.actions_volleyball import classifier, detect, evaluate
from vball.paths import MODELS


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect")
    d.add_argument("--videos", required=True)
    d.add_argument("--pkl", required=True)
    d.add_argument("--model", default=str(MODELS / "action_yolo11m.pt"))
    d.add_argument("--out", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--pkl", required=True)
    e.add_argument("--ann", required=True)
    e.add_argument("--dets", required=True)
    e.add_argument("--ball-preds", default=None)
    e.add_argument("--out", default="actions_volleyball.json")
    c = sub.add_parser("classifier")
    c.add_argument("--pkl", required=True)
    c.add_argument("--ann", required=True)
    c.add_argument("--probs", required=True)
    c.add_argument("--k", type=float, default=2.0)
    c.add_argument("--floor", type=float, default=0.6)
    c.add_argument(
        "--ball-preds", nargs="*", help="detected balls (eval_ball_detection outputs) to compare with labelled ones"
    )
    c.add_argument("--bootstrap", type=int, default=0, help="resamples of whole matches for 95%% intervals (0: none)")
    c.add_argument("--out", default="actions_volleyball_classifier.json")
    args = ap.parse_args()
    {"detect": detect, "evaluate": evaluate, "classifier": classifier}[args.cmd](args)


if __name__ == "__main__":
    main()
