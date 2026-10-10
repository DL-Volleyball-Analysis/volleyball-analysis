"""Render an analysed video with every result drawn on it, for sharing outside the app.

Draws the ball trail (VballNet), player boxes and track ids, the court lines of shots whose court status is
ok, a top-down court map with the players' positions (and the ball from 3D flights when there are any), and a
status bar that says what each overlay is and why something is missing. Doubtful courts are named, never drawn.

  python backend/render.py broadcast_side_high_men [--out path.mp4]
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from vball import court as vcourt
from vball import court_registration

import pipeline
from database import Database
from settings import DB_PATH, RESULTS

BALL, EDGE, WHITE = (63, 210, 255), (0, 0, 0), (255, 255, 255)  # BGR
TEAM = {"a": (163, 118, 15), "b": (57, 18, 159), "": (230, 230, 230)}  # side of the net, as in the app
TRAIL_S = 0.5
JUMP = 0.08  # a trail segment longer than this share of the width is a false detection: not drawn
COURT_STATUS = {"ok": "court found", "needs_review": "court doubtful, not drawn", "failed": "court not found"}


def load(vid: str) -> dict:
    res = RESULTS / vid
    out = {name: pipeline.load_stage(res, name) for name in pipeline.STAGES}
    out["ball_df"] = pd.read_csv(res / "ball.csv") if (res / "ball.csv").exists() else None
    out["players_df"] = pd.read_csv(res / "players.csv.gz") if (res / "players.csv.gz").exists() else None
    out["flights"] = json.loads((res / "flights.json").read_text()) if (res / "flights.json").exists() else []
    return out


def ball_positions(df: pd.DataFrame | None, n: int) -> np.ndarray:
    uv = np.full((n, 2), np.nan)
    if df is not None:
        seen = df[(df["visible"] > 0) & (df["frame"] < n)]
        uv[seen["frame"].to_numpy(int)] = seen[["x", "y"]].to_numpy(float)
    return uv


def flight_ground(flights: list[dict], frame: int, fps: float):
    for f in flights:
        if f["start_frame"] <= frame <= f["end_frame"]:
            t = (frame - f["start_frame"]) / fps
            p = np.array(f["p0"]) + np.array(f["v0"]) * t + 0.5 * np.array([0, 0, -9.81]) * t * t
            return p, f["quality"]
    return None, None


class CourtMap:
    """Top-down court in the corner: 18 x 9 m plus a 2 m free zone."""

    def __init__(self, width: int):
        self.s = width / 22.0
        self.w, self.h = width, int(13 * self.s)

    def px(self, x, y):
        return int((x + 2) * self.s), int((11 - y) * self.s)  # far sideline (y = 9) at the top

    def draw(self, people, ball, ball_quality) -> np.ndarray:
        img = np.full((self.h, self.w, 3), (238, 238, 238), np.uint8)
        cv2.rectangle(img, self.px(0, 9), self.px(18, 0), (205, 216, 236), -1)
        for (x1, y1), (x2, y2) in vcourt.LINES.values():
            cv2.line(img, self.px(x1, y1), self.px(x2, y2), (90, 90, 90), 1, cv2.LINE_AA)
        cv2.line(img, self.px(9, -0.6), self.px(9, 9.6), (20, 20, 20), 2, cv2.LINE_AA)
        for x, y, side in people:
            cv2.circle(img, self.px(x, y), max(3, int(self.s * 0.35)), TEAM.get(side, WHITE), -1, cv2.LINE_AA)
        if ball is not None:
            cv2.circle(img, self.px(ball[0], ball[1]), max(3, int(self.s * 0.3)), BALL, -1, cv2.LINE_AA)
            cv2.putText(img, f"{ball[2]:.1f} m{' ?' if ball_quality == 'low' else ''}", self.px(ball[0] + 0.5, ball[1] + 0.5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 30, 30), 1, cv2.LINE_AA)
        cv2.rectangle(img, (0, 0), (self.w - 1, self.h - 1), (120, 120, 120), 1)
        return img


def text(img, s, org, scale, color=WHITE, thick=1):
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, EDGE, thick + 2, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def render(vid: str, path: Path, out: Path) -> Path:
    r = load(vid)
    meta = r["decode"]
    fps, n, size = meta["fps"], meta["frames"], (meta["width"], meta["height"])
    w, h = size
    uv = ball_positions(r["ball_df"], n)
    pdf = r["players_df"]
    by_frame = {f: g for f, g in pdf.groupby("frame")} if pdf is not None else {}
    court = r["court"] if r["court"] and r["court"].get("status") == "done" else None
    cmap = CourtMap(int(w * 0.24))
    scale = h / 1080
    trail = int(TRAIL_S * fps)

    tmp = out.with_suffix(".raw.mp4")
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    cap = cv2.VideoCapture(str(path))
    for i in range(n):
        ok, img = cap.read()
        if not ok:
            break
        shot = court_registration._shot_of(court, i) if court else None
        status = shot["status"] if shot else None
        H = court_registration.mapping_at(court, i, size)
        if H is not None:
            img = vcourt.draw(img, H, color=(0, 255, 255), thickness=max(1, int(2 * scale)))

        people = []
        others = []
        for row in (by_frame.get(i).itertuples() if i in by_frame else []):
            p1, p2 = (int(row.x1), int(row.y1)), (int(row.x2), int(row.y2))
            if getattr(row, "role", "player") == "other":  # officials, staff, spectators: faint, unlabelled
                others.append((p1, p2))
                continue
            side = row.side if isinstance(row.side, str) else ""
            col = TEAM.get(side, WHITE) if row.placed else WHITE
            cv2.rectangle(img, p1, p2, EDGE, max(2, int(3 * scale)))
            cv2.rectangle(img, p1, p2, col, max(1, int(1.5 * scale)))
            # a tracking id, not the shirt number
            text(img, f"ID {int(row.track_id)}", (p1[0], p1[1] - int(6 * scale)), 0.5 * scale)
            if row.placed and not np.isnan(row.court_x):
                people.append((row.court_x, row.court_y, side))
        if others:
            faint = img.copy()
            for p1, p2 in others:
                cv2.rectangle(faint, p1, p2, (150, 150, 150), max(1, int(1.5 * scale)))
            img = cv2.addWeighted(faint, 0.4, img, 0.6, 0)

        pts = [(int(x), int(y)) for x, y in uv[max(0, i - trail):i + 1] if not np.isnan(x)]
        for k in range(1, len(pts)):
            if np.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]) > JUMP * w:
                continue
            cv2.line(img, pts[k - 1], pts[k], EDGE, max(3, int(6 * scale)), cv2.LINE_AA)
            cv2.line(img, pts[k - 1], pts[k], BALL, max(2, int(3 * scale)), cv2.LINE_AA)
        if not np.isnan(uv[i, 0]):
            cv2.circle(img, (int(uv[i, 0]), int(uv[i, 1])), int(10 * scale), BALL, max(2, int(3 * scale)), cv2.LINE_AA)

        ground, quality = flight_ground(r["flights"], i, fps)
        mini = cmap.draw(people, ground, quality)
        x0, y0 = w - cmap.w - int(16 * scale), h - cmap.h - int(16 * scale)
        img[y0:y0 + cmap.h, x0:x0 + cmap.w] = mini

        bar = np.zeros((int(44 * scale), w, 3), np.uint8)
        img[:bar.shape[0]] = (img[:bar.shape[0]] * 0.35).astype(np.uint8)
        court_txt = COURT_STATUS.get(status, "no court model") if court else "court: not available"
        placed = "positions on the map" if people else "no court positions (court not usable)"
        text(img, f"{i / fps:5.1f} s   ball: VballNet V4c   players: YOLO26s + BoT-SORT (ID = tracking id), {placed}   {court_txt}",
             (int(14 * scale), int(29 * scale)), 0.62 * scale)
        writer.write(img)
    cap.release()
    writer.release()
    if shutil.which("ffmpeg"):  # H.264 plays in browsers and on phones; OpenCV's mp4v often does not
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "22", str(out)], check=True)
        tmp.unlink()
    else:
        tmp.rename(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="video name (as in the library) or id")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    v = next((x for x in Database(DB_PATH).list_videos() if args.video in (x["id"], x["name"])), None)
    if v is None:
        raise SystemExit(f"no video {args.video!r}")
    out = args.out or (RESULTS / v["id"] / f"{v['name']}_analysis.mp4")
    print(render(v["id"], Path(v["path"]), out))


if __name__ == "__main__":
    main()
