"""Project locations. Everything else imports paths from here."""
import os
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


# The Google Drive desktop folder that Colab sees as /content/drive/MyDrive: VBALL_DRIVE_ACCOUNT if set, else the
# only Drive account found.
DRIVE_ACCOUNT_ENV = "VBALL_DRIVE_ACCOUNT"


def drive_root() -> Path:
    """'My Drive' is localised by the Drive app (e.g. 我的雲端硬碟), so find it instead of hard-coding."""
    if os.environ.get(DRIVE_ACCOUNT_ENV):
        accounts = [Path(os.environ[DRIVE_ACCOUNT_ENV])]
    else:
        accounts = sorted((Path.home() / "Library/CloudStorage").glob("GoogleDrive-*"))
    if len(accounts) != 1:
        raise SystemExit(f"set {DRIVE_ACCOUNT_ENV} to the Google Drive folder to use (found {len(accounts)})")
    for name in ("My Drive", "我的雲端硬碟"):
        if (accounts[0] / name).is_dir():
            return accounts[0] / name
    raise SystemExit(f"no 'My Drive' folder under {accounts[0]}")
