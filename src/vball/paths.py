"""Project locations. Everything else imports paths from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
VIDEOS = ROOT / "data" / "videos"
DATASETS = ROOT / "data" / "datasets"
OUTPUTS = ROOT / "outputs"
EXTERNAL = ROOT / "external"

# Upstream VballNet inference (asigatchov/fast-volleyball-tracking-inference, MIT)
VBALLNET_SRC = EXTERNAL / "fast-volleyball-tracking-inference" / "src"

BALL_MODELS = {
    "v4c": MODELS / "vballnet_v4c.onnx",          # F1 0.902, ~150 FPS CPU (upstream benchmark)
    "fast_v1": MODELS / "vballnet_fast_v1.onnx",  # model family used in the original capstone
}
