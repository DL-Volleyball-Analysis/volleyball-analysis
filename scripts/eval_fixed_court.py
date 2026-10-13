"""Court error in metres on the fixed end-line clips from hand-labelled floor points (verify-court-by-lines, task 3.1).

  .venv/bin/python scripts/eval_fixed_court.py --make            # plates + label.html in outputs/court/fixed_labels/
  (open label.html, click the points, save labels.json next to it)
  .venv/bin/python scripts/eval_fixed_court.py                   # error per clip from labels.json

The court is the web app's analysis result of each clip (its court stage, line evidence included).
"""

import argparse
import base64
import json
from pathlib import Path

import cv2

from vball import court_lines, court_registration, pipeline
from vball.evaluation.court_points import POINTS, errors, summary
from vball.paths import OUTPUTS

FOLDER = OUTPUTS / "court" / "fixed_labels"


def clips() -> list[dict]:
    """The app's analysed fixed clips: name, video, results folder, the shot to label (the longest ok one)."""
    from vball_app.db import Database
    from vball_app.settings import DB_PATH, RESULTS

    out = []
    for v in Database(DB_PATH).list_videos():
        if not v["name"].startswith("fixed_"):
            continue
        court = pipeline.load_stage(RESULTS / v["id"], "court") or {}
        ok = [s for s in court.get("shots", []) if s.get("status") == "ok"]
        if ok:
            shot = max(ok, key=lambda s: s["end_frame"] - s["start_frame"])
            out.append({"name": v["name"], "video": v["path"], "results": RESULTS / v["id"], "shot": shot})
    return sorted(out, key=lambda c: c["name"])


def make() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    images = {}
    for c in clips():
        plate = court_lines.background_plate(Path(c["video"]), c["shot"]["start_frame"], c["shot"]["end_frame"])
        cv2.imwrite(str(FOLDER / f"{c['name']}.jpg"), plate, [cv2.IMWRITE_JPEG_QUALITY, 92])
        ok, buf = cv2.imencode(".jpg", plate, [cv2.IMWRITE_JPEG_QUALITY, 92])
        images[c["name"]] = base64.b64encode(buf.tobytes()).decode()
        print(f"{c['name']}: plate of frames {c['shot']['start_frame']}-{c['shot']['end_frame']}")
    page = (Path(__file__).with_name("label_court_points.html")).read_text()
    page = page.replace("/*IMAGES*/{}", json.dumps(images)).replace("/*POINTS*/[]", json.dumps(list(POINTS)))
    (FOLDER / "label.html").write_text(page)
    print(f"open {FOLDER / 'label.html'} and save labels.json in {FOLDER}")


def evaluate(labels_path: Path) -> None:
    labels = json.loads(labels_path.read_text())
    rows = {}
    for c in clips():
        if c["name"] not in labels:
            continue
        meta = pipeline.load_stage(c["results"], "decode")
        court = pipeline.load_stage(c["results"], "court")
        mid = (c["shot"]["start_frame"] + c["shot"]["end_frame"]) // 2
        H = court_registration.mapping_at(court, mid, (meta["width"], meta["height"]))
        per = errors(H, labels[c["name"]])
        rows[c["name"]] = {
            "source": c["shot"].get("source"),
            **summary(per),
            "per_point": {k: round(v, 3) for k, v in per.items()},
        }
        print(f"{c['name']:24s} {json.dumps({k: v for k, v in rows[c['name']].items() if k != 'per_point'})}")
    (FOLDER / "errors.json").write_text(json.dumps(rows, indent=2))
    print(f"written {FOLDER / 'errors.json'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--make", action="store_true", help="write the plates and the labelling page")
    ap.add_argument("--labels", type=Path, default=FOLDER / "labels.json")
    args = ap.parse_args()
    make() if args.make else evaluate(args.labels)


if __name__ == "__main__":
    main()
