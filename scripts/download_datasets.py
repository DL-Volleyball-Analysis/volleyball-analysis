"""Download Roboflow volleyball court keypoint datasets (CC BY 4.0) into data/datasets/.

Needs ROBOFLOW_API_KEY in the environment (set in ~/.zshrc, never in code).
Usage: zsh -ic '.venv/bin/python scripts/download_datasets.py'

The roboflow SDK download hung on a large zip, so this asks the REST API for the export
link and fetches it with curl (resumable, retried). URLs are never printed: the API
request carries the key.
"""
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball.paths import DATASETS  # noqa: E402

API = "https://api.roboflow.com"
EXPORT_FORMAT = "yolov8"  # YOLO pose txt labels + data.yaml with kpt_shape / flip_idx
COURT_KEYPOINT_SETS = [
    ("volleyballcourt", "volleyball-court-keypoints-k6y7r"),           # 495 images
    ("primaryws", "volleyball_court_key_points_regression_dataset"),  # 862 images (used by Volleyball-Metrics)
]


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def latest_version(key: str, workspace: str, project: str) -> int:
    info = get_json(f"{API}/{workspace}/{project}?api_key={key}")
    return max(int(v["id"].rsplit("/", 1)[-1]) for v in info["versions"])


def export_link(key: str, workspace: str, project: str, version: int) -> str:
    # The first request may only start the export; Roboflow returns the link once it is ready.
    for _ in range(30):
        info = get_json(f"{API}/{workspace}/{project}/{version}/{EXPORT_FORMAT}?api_key={key}")
        link = info.get("export", {}).get("link")
        if link:
            return link
        subprocess.run(["sleep", "10"], check=True)
    raise RuntimeError("export not ready after 5 minutes")


def download(url: str, zip_path: Path) -> None:
    subprocess.run(
        ["curl", "-sS", "-L", "--fail", "-C", "-", "--retry", "5", "--retry-all-errors",
         "--speed-limit", "10000", "--speed-time", "60", "-o", str(zip_path), url],
        check=True,
    )


def main():
    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit("ROBOFLOW_API_KEY is not set")
    DATASETS.mkdir(parents=True, exist_ok=True)
    for workspace, project in COURT_KEYPOINT_SETS:
        try:
            version = latest_version(key, workspace, project)
            dest = DATASETS / f"{project}-v{version}"
            if (dest / "data.yaml").exists():
                print(f"{project}: already downloaded")
                continue
            dest.mkdir(parents=True, exist_ok=True)
            zip_path = dest / "roboflow.zip"
            download(export_link(key, workspace, project, version), zip_path)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(dest)
            zip_path.unlink()
            print(f"{project}: v{version} -> {dest}")
        except Exception as e:  # keep going if one dataset is private or renamed
            msg = str(e).replace(key, "***")
            print(f"{project}: FAILED ({type(e).__name__}: {msg:.150})")


if __name__ == "__main__":
    main()
