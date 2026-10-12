"""Render an analysed video with every result drawn on it, for sharing outside the app.

Draws the ball trail (VballNet), player boxes with shirt numbers or track ids and their current action, the court
lines of shots whose court status is ok, a top-down court map with the players' positions (and the ball from 3D
flights when there are any), a 3D view of the court with the current 3D flight, and a status bar that says what each
overlay is and why something is missing. Doubtful courts are named, never drawn.

  python -m vball_app.render broadcast_side_high_men [--out path.mp4]
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd

from vball import court as vcourt
from vball import court_registration, pipeline
from vball.paths import OUTPUTS

from .db import Database
from .settings import DB_PATH, RESULTS

BALL, EDGE, WHITE = (63, 210, 255), (0, 0, 0), (255, 255, 255)  # BGR
TEAM = {"a": (163, 118, 15), "b": (57, 18, 159), "": (230, 230, 230)}  # side of the net, as in the app
TRAIL_S = 0.5
JUMP = 0.08  # a trail segment longer than this share of the width is a false detection: not drawn
COURT_STATUS = {"ok": "court found", "needs_review": "court doubtful, not drawn", "failed": "court not found"}


def load(vid: str) -> dict:
    res = RESULTS / vid
    out: dict[str, Any] = {name: pipeline.load_stage(res, name) for name in pipeline.STAGES}
    out["ball_df"] = pd.read_csv(res / "ball.csv") if (res / "ball.csv").exists() else None
    out["players_df"] = pd.read_csv(res / "players.csv.gz") if (res / "players.csv.gz").exists() else None
    out["flights"] = json.loads((res / "flights.json").read_text()) if (res / "flights.json").exists() else []
    out["actions"] = (
        json.loads((res / "action_events.json").read_text()) if (res / "action_events.json").exists() else {}
    )
    out["court"] = pipeline.corrected_court(out["court"], out["decode"], Database(DB_PATH).court_corrections(vid), res)
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
        img: np.ndarray = np.full((self.h, self.w, 3), (238, 238, 238), np.uint8)
        cv2.rectangle(img, self.px(0, 9), self.px(18, 0), (205, 216, 236), -1)
        for (x1, y1), (x2, y2) in vcourt.LINES.values():
            cv2.line(img, self.px(x1, y1), self.px(x2, y2), (90, 90, 90), 1, cv2.LINE_AA)
        cv2.line(img, self.px(9, -0.6), self.px(9, 9.6), (20, 20, 20), 2, cv2.LINE_AA)
        for x, y, side in people:
            cv2.circle(img, self.px(x, y), max(3, int(self.s * 0.35)), TEAM.get(side, WHITE), -1, cv2.LINE_AA)
        if ball is not None:
            cv2.circle(img, self.px(ball[0], ball[1]), max(3, int(self.s * 0.3)), BALL, -1, cv2.LINE_AA)
            cv2.putText(
                img,
                f"{ball[2]:.1f} m{' ?' if ball_quality == 'low' else ''}",
                self.px(ball[0] + 0.5, ball[1] + 0.5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (30, 30, 30),
                1,
                cv2.LINE_AA,
            )
        cv2.rectangle(img, (0, 0), (self.w - 1, self.h - 1), (120, 120, 120), 1)
        return img


def flight_at(flights: list[dict], frame: int) -> dict | None:
    return next((f for f in flights if f["start_frame"] <= frame <= f["end_frame"]), None)


def flight_points(f: dict, fps: float, until: int | None = None) -> np.ndarray:
    """(n, 3) positions of a flight, every frame from its start to `until` (default its end)."""
    end = f["end_frame"] if until is None else until
    t = np.arange(0, end - f["start_frame"] + 1) / fps
    return np.array(f["p0"]) + np.outer(t, f["v0"]) + 0.5 * np.outer(t * t, [0, 0, -9.81])


class Court3D:
    """A 3D view of the court from a fixed virtual camera behind a corner: floor, lines, net, players (as posts of
    1.8 m) and the current 3D flight (whole path faint, the part flown so far solid, the ball, its shadow and height)."""

    NET_TOP, NET_BAND = 2.43, 1.0

    def __init__(self, width: int):
        from vball.calibration import look_at

        self.w, self.h = width, int(width * 0.62)
        self.cam = look_at([-7.0, -9.0, 9.0], [9.0, 4.5, 0.5], 0.95 * width, (self.w, self.h))

    def px(self, pts) -> np.ndarray:
        return self.cam.project(np.atleast_2d(np.asarray(pts, float))).astype(np.int32)

    def draw(self, people, flight: dict | None, frame: int, fps: float, note: str) -> np.ndarray:
        img: np.ndarray = np.full((self.h, self.w, 3), (238, 238, 238), np.uint8)
        floor = self.px([[-2, -2, 0], [20, -2, 0], [20, 11, 0], [-2, 11, 0]])
        cv2.fillPoly(img, [floor], (225, 225, 225))
        cv2.fillPoly(img, [self.px([[0, 0, 0], [18, 0, 0], [18, 9, 0], [0, 9, 0]])], (205, 216, 236))
        for (x1, y1), (x2, y2) in vcourt.LINES.values():
            a, b = self.px([[x1, y1, 0], [x2, y2, 0]])
            cv2.line(img, tuple(a), tuple(b), (90, 90, 90), 1, cv2.LINE_AA)
        for x, y, side in people:
            a, b = self.px([[x, y, 0], [x, y, 1.8]])
            cv2.line(img, tuple(a), tuple(b), TEAM.get(side, WHITE), max(2, self.w // 120), cv2.LINE_AA)
        if flight is not None:  # behind the net from this view when x > 9: drawn before the net
            path = flight_points(flight, fps)
            q = self.px(path)
            cv2.polylines(img, [q], False, (150, 170, 190), 1, cv2.LINE_AA)
            done = self.px(flight_points(flight, fps, frame))
            cv2.polylines(img, [done], False, BALL, 2, cv2.LINE_AA)
            p = flight_points(flight, fps, frame)[-1]
            shadow = self.px([[p[0], p[1], 0]])[0]
            cv2.ellipse(img, tuple(shadow), (5, 2), 0, 0, 360, (120, 120, 120), -1, cv2.LINE_AA)
            cv2.line(img, tuple(shadow), tuple(self.px([p])[0]), (160, 160, 160), 1, cv2.LINE_AA)
            cv2.circle(img, tuple(self.px([p])[0]), max(4, self.w // 70), BALL, -1, cv2.LINE_AA)
            cv2.circle(img, tuple(self.px([p])[0]), max(4, self.w // 70), EDGE, 1, cv2.LINE_AA)
            low = " (low quality)" if flight.get("quality") == "low" else ""
            cv2.putText(
                img,
                f"ball {p[2]:.1f} m high{low}",
                (8, self.h - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (30, 30, 30),
                1,
                cv2.LINE_AA,
            )
        net = self.px(
            [
                [9, -0.5, self.NET_TOP - self.NET_BAND],
                [9, 9.5, self.NET_TOP - self.NET_BAND],
                [9, 9.5, self.NET_TOP],
                [9, -0.5, self.NET_TOP],
            ]
        )
        band = img.copy()
        cv2.fillPoly(band, [net], (60, 60, 60))
        img = cv2.addWeighted(band, 0.25, img, 0.75, 0)
        cv2.line(img, tuple(net[3]), tuple(net[2]), (40, 40, 40), 2, cv2.LINE_AA)
        for y in (-0.5, 9.5):
            a, b = self.px([[9, y, 0], [9, y, self.NET_TOP]])
            cv2.line(img, tuple(a), tuple(b), (40, 40, 40), 2, cv2.LINE_AA)
        cv2.putText(img, "3D", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        if flight is None:
            cv2.putText(img, note, (8, self.h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1, cv2.LINE_AA)
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
    c3d = Court3D(int(w * 0.26))
    traj = r.get("trajectory") or {}
    no_3d = (
        "no 3D flight at this moment"
        if r["flights"]
        else "no 3D: " + (traj.get("message") or "no flights").split(",")[0][:60]
    )
    from vball import jersey

    segs = {int(t): [tuple(x) for x in sg] for t, sg in (r["actions"].get("segments") or {}).items()}
    reach = int(r["actions"].get("reach", 0))
    doing: dict[tuple[int, int], str] = {}  # (track, frame) -> action, for the frames of each event
    for e in r["actions"].get("events") or []:
        if e.get("track_id") is not None:
            for f in range(e["start_frame"], e["end_frame"] + 1):
                doing[(int(e["track_id"]), f)] = e["action"]
    scale = h / 1080
    trail = int(TRAIL_S * fps)

    out.parent.mkdir(parents=True, exist_ok=True)  # VideoWriter fails silently into a missing folder
    tmp = out.with_suffix(".raw.mp4")
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter.fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise OSError(f"cannot write {tmp}")
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
        for row in by_frame[i].itertuples() if i in by_frame else []:
            p1, p2 = (int(row.x1), int(row.y1)), (int(row.x2), int(row.y2))
            if getattr(row, "role", "player") == "other":  # officials, staff, spectators: faint, unlabelled
                others.append((p1, p2))
                continue
            side = row.side if isinstance(row.side, str) else ""
            col = TEAM.get(side, WHITE) if row.placed else WHITE
            cv2.rectangle(img, p1, p2, EDGE, max(2, int(3 * scale)))
            cv2.rectangle(img, p1, p2, col, max(1, int(1.5 * scale)))
            tid = int(row.track_id)
            n = jersey.number_at(segs[tid], i, reach) if tid in segs else None
            label = jersey.label(tid, n)  # time-local shirt number when the vote is clear, else the tracking id
            if (tid, i) in doing:
                label += f" {doing[(tid, i)]}"
            text(img, label, (p1[0], p1[1] - int(6 * scale)), 0.5 * scale)
            if row.placed and not np.isnan(row.court_x):
                people.append((row.court_x, row.court_y, side))
        if others:
            faint = img.copy()
            for p1, p2 in others:
                cv2.rectangle(faint, p1, p2, (150, 150, 150), max(1, int(1.5 * scale)))
            img = cv2.addWeighted(faint, 0.4, img, 0.6, 0)

        pts = [(int(x), int(y)) for x, y in uv[max(0, i - trail) : i + 1] if not np.isnan(x)]
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
        img[y0 : y0 + cmap.h, x0 : x0 + cmap.w] = mini
        view = c3d.draw(people, flight_at(r["flights"], i), i, fps, no_3d)
        x1, y1 = int(16 * scale), h - c3d.h - int(16 * scale)
        img[y1 : y1 + c3d.h, x1 : x1 + c3d.w] = view

        bar = np.zeros((int(44 * scale), w, 3), np.uint8)
        img[: bar.shape[0]] = (img[: bar.shape[0]] * 0.35).astype(np.uint8)
        court_txt = COURT_STATUS.get(status or "", "no court model") if court else "court: not available"
        placed = "positions on the map" if people else "no court positions (court not usable)"
        text(
            img,
            f"{i / fps:5.1f} s   ball: VballNet V4c   players: YOLO26s + BoT-SORT (#n shirt, ID n tracking id), {placed}   {court_txt}",
            (int(14 * scale), int(29 * scale)),
            0.62 * scale,
        )
        writer.write(img)
    cap.release()
    writer.release()
    if shutil.which("ffmpeg"):  # H.264 plays in browsers and on phones; OpenCV's mp4v often does not
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(tmp),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "22",
                str(out),
            ],
            check=True,
        )
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
    out = args.out or (OUTPUTS / "videos" / f"{v['name']}_analysis.mp4")
    print(render(v["id"], Path(v["path"]), out))


if __name__ == "__main__":
    main()
