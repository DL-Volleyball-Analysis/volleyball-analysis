"""Pipeline settings: model files, sampling rates and detector settings.

Stages read these as `config.NAME` at call time, so a test or a script can replace one (monkeypatch.setattr).
"""
from vball import actors, players
from vball.paths import MODELS

BALL_MODEL = "v4c"
# the installed court keypoint model: copy the chosen weights here (models/ is not in git)
# Every installed court model registers every shot; court_registration.pick keeps the best per shot. v2 is right
# on gym images (0.49 m) and v3b on broadcast clips (0.10 m); neither does both (docs/results/court-keypoints.md).
COURT_MODELS = {"gym": MODELS / "court_kpt.pt", "broadcast": MODELS / "court_kpt_broadcast.pt"}
# capstone action recogniser (test mAP@0.5 0.957, same matches as training) and the retrained digit detector;
# shirt numbers are read only once the digit model is installed (docs/results/actions.md)
RALLY_MODEL = MODELS / "rally_cues_hgb.joblib"  # docs/results/rallies.md
ACTION_MODEL = MODELS / "action_yolo11m.pt"  # serves (the person classifier has no serve class)
PERSON_MODEL = MODELS / "person_action_yolo26s_cls.pt"  # block / receive / set / spike per player (docs/results/actions.md)
BALL_PRIOR = actors.ActorConfig(k=2.0, floor=0.6)  # chosen on the Volleyball dataset's validation matches
JERSEY_MODEL = MODELS / "jersey_digits_yolo26s.pt"
ACTION_FPS, JERSEY_FPS = 10.0, 2.0
SERVE_FPS = 3.0  # the action detector, which only gives serves next to the classifier (speed-up-analysis)
# YOLO26s fine-tuned on SportsMOT volleyball training sequences (players only): IDF1 0.690, precision 0.970 on
# SportsMOT volleyball val, against 0.484 / 0.614 for the COCO weights (docs/results/player-tracking.md)
GENERAL_PLAYER_MODEL = MODELS / "yolo26s.pt"  # COCO persons: fallback where the player-only detector misses players
PLAYER_CFG = players.TrackerConfig(model=str(MODELS / "player_yolo26s_sportsmot.pt"), imgsz=960, tracker="botsort.yaml", det_fps=10.0)

MOTION_FILE = "camera_motion.npz"
SHOT_CUT_CORRELATION = 0.6  # HSV histogram correlation below this between frames = camera cut
