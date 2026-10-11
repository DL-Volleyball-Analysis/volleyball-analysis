"""Ball candidates per frame from a ball detector; `vball.ball_track` decides which candidate is the ball.

Two detector families, both from asigatchov/fast-volleyball-tracking-inference (MIT), read as ONNX:
  VballNet   9 grey frames resized to 512 x 288 -> one heatmap per frame. On a 1080p broadcast that is a 3.75x
             reduction (a 20 px ball becomes 5 px, on wide shots 2-3 px). `grid` additionally runs the model on
             overlapping tiles (2 x 2: a 1.9x reduction), which keeps the ball larger but adds ball-like false
             candidates (floor dashes, scoreboard digits).
  Ravel      RAVEL-VB releases: 9 frames (011: 1024 x 576 grey; 012: 640 x 360 RGB) -> a coarse ball grid with
             a confidence and a sub-cell offset per cell. Local maxima above `threshold` are the candidates.
  Wasb       WASB (Tarashima et al., BMVC 2023; HRNet with high-resolution features): 3 RGB frames at 512 x 288,
             ImageNet-normalised -> one heatmap per frame (sigmoid applied in the exported model).

    det = load("ravel012")                       # or "v4c", "v4c-tiles", "ravel011"
    cands = det.candidates(bgr_frames)           # per frame: [Candidate(x, y, score), ...]
"""
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .paths import BALL_MODELS

SEQ = 9


@dataclass(frozen=True)
class Candidate:
    x: float      # original image pixels
    y: float
    score: float  # detector confidence (peak heatmap value / grid confidence)


def _session(path: Path):
    import onnxruntime as ort
    providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
    return ort.InferenceSession(str(path), providers=providers)


def _windows(n: int):
    """(start, stop) of consecutive windows of SEQ frames; the last one is padded by the caller."""
    return [(s, min(n, s + SEQ)) for s in range(0, n, SEQ)]


def _pad(xs: list) -> list:
    return xs + [xs[-1]] * (SEQ - len(xs))


def views(width: int, height: int, grid: tuple[int, int] | None, overlap: float = 0.15) -> list[tuple[int, int, int, int]]:
    """(x, y, w, h) rectangles: the whole frame, plus a rows x cols grid of tiles overlapping by `overlap`."""
    out = [(0, 0, width, height)]
    if grid:
        rows, cols = grid
        th, tw = min(height, int(height / rows * (1 + overlap))), min(width, int(width / cols * (1 + overlap)))
        for y in np.linspace(0, height - th, rows).astype(int):
            for x in np.linspace(0, width - tw, cols).astype(int):
                out.append((int(x), int(y), tw, th))
    return out


def blobs(heatmap: np.ndarray, threshold: float = 0.5) -> list[tuple[float, float, float]]:
    """(x, y, peak) of each connected region above threshold, in heatmap pixels."""
    mask = (heatmap >= threshold).astype(np.uint8)
    n, labels, _, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    return [(float(centroids[k][0]), float(centroids[k][1]), float(heatmap[labels == k].max())) for k in range(1, n)]


def merge(cands: list[Candidate], radius: float) -> list[Candidate]:
    """One candidate per ball-sized neighbourhood (the same ball seen by the frame and by overlapping tiles):
    keep the highest score."""
    out: list[Candidate] = []
    for c in sorted(cands, key=lambda c: -c.score):
        if all(np.hypot(c.x - o.x, c.y - o.y) > radius for o in out):
            out.append(c)
    return out


class VballNet:
    IN_W, IN_H = 512, 288

    def __init__(self, path: str | Path, grid: tuple[int, int] | None = None, threshold: float = 0.5,
                 merge_px: float = 12.0):
        self.session = _session(path)
        self.input = self.session.get_inputs()[0].name
        self.grid, self.threshold, self.merge_px = grid, threshold, merge_px

    def heatmaps(self, crops: list[np.ndarray]) -> np.ndarray:
        """Up to 9 grey crops of one view -> (len(crops), 288, 512) heatmaps."""
        x = [cv2.resize(c, (self.IN_W, self.IN_H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 for c in crops]
        return self.session.run(None, {self.input: np.stack(_pad(x))[None]})[0][0, :len(crops)]

    def candidates(self, frames: list[np.ndarray]) -> list[list[Candidate]]:
        if not frames:
            return []
        grey = [f if f.ndim == 2 else cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
        h, w = grey[0].shape
        raw: list[list[Candidate]] = [[] for _ in grey]
        for s, e in _windows(len(grey)):
            for (x0, y0, vw, vh) in views(w, h, self.grid):
                for i, m in enumerate(self.heatmaps([g[y0:y0 + vh, x0:x0 + vw] for g in grey[s:e]])):
                    raw[s + i] += [Candidate(x0 + bx * vw / self.IN_W, y0 + by * vh / self.IN_H, p)
                                   for bx, by, p in blobs(m, self.threshold)]
        return [merge(c, self.merge_px) for c in raw]


class Ravel:
    def __init__(self, path: str | Path, threshold: float = 0.3, top_k: int = 5):
        path = Path(path)
        cfg = json.loads(path.with_suffix(".json").read_text())["config"]
        self.w, self.h, self.channels = int(cfg["image_width"]), int(cfg["image_height"]), int(cfg["input_channels"])
        self.session = _session(path)
        self.threshold, self.top_k = threshold, top_k

    def prep(self, f: np.ndarray) -> np.ndarray:
        """As upstream: INTER_AREA when shrinking, [0, 1], grey (1 x H x W) or RGB (3 x H x W)."""
        if f.ndim == 2:
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
        shrink = self.w <= f.shape[1] and self.h <= f.shape[0]
        r = cv2.resize(f, (self.w, self.h), interpolation=cv2.INTER_AREA if shrink else cv2.INTER_LINEAR)
        x = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)[None] if self.channels == 1 else cv2.cvtColor(r, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)
        return x.astype(np.float32) / 255.0

    def candidates(self, frames: list[np.ndarray]) -> list[list[Candidate]]:
        if not frames:
            return []
        fh, fw = frames[0].shape[:2]
        out: list[list[Candidate]] = []
        for s, e in _windows(len(frames)):
            x = np.stack(_pad([self.prep(f) for f in frames[s:e]]))[None]
            names = [o.name for o in self.session.get_outputs()]
            grid = dict(zip(names, self.session.run(None, {"frames": x})))["ball_grid"][0]
            for g in grid[:e - s]:
                conf = g[0]
                peaks = (conf == cv2.dilate(conf, np.ones((3, 3), np.float32))) & (conf >= self.threshold)
                rows, cols = np.nonzero(peaks)
                cs = [Candidate((c + g[1, r, c]) / conf.shape[1] * fw, (r + g[2, r, c]) / conf.shape[0] * fh, float(conf[r, c]))
                      for r, c in zip(rows, cols)]
                out.append(sorted(cs, key=lambda c: -c.score)[:self.top_k])
        return out


def letterbox(width: int, height: int, out_w: int, out_h: int) -> tuple[float, int, int]:
    """(scale, x0, y0) placing a width x height frame centred in out_w x out_h without distortion; an image point
    p maps to p * scale + (x0, y0). Shared by inference (Wasb) and training data (scripts/build_ball_clips.py)."""
    s = min(out_w / width, out_h / height)
    return s, (out_w - round(width * s)) // 2, (out_h - round(height * s)) // 2


def letterbox_image(f: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    h, w = f.shape[:2]
    s, x0, y0 = letterbox(w, h, out_w, out_h)
    canvas = np.zeros((out_h, out_w) + f.shape[2:], f.dtype)
    nw, nh = round(w * s), round(h * s)
    canvas[y0:y0 + nh, x0:x0 + nw] = cv2.resize(f, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return canvas


class Wasb:
    W, H, FRAMES = 512, 288, 3
    MEAN = np.array([0.485, 0.456, 0.406], np.float32)
    STD = np.array([0.229, 0.224, 0.225], np.float32)

    def __init__(self, path: str | Path, threshold: float = 0.5, merge_px: float = 12.0):
        self.session = _session(path)
        self.input = self.session.get_inputs()[0].name
        self.threshold, self.merge_px = threshold, merge_px

    def prep(self, f: np.ndarray) -> np.ndarray:
        """3 x H x W, RGB, ImageNet-normalised; the frame is letterboxed to 512 x 288 like WASB's affine input."""
        if f.ndim == 2:
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(letterbox_image(f, self.W, self.H), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return ((rgb - self.MEAN) / self.STD).transpose(2, 0, 1)

    def candidates(self, frames: list[np.ndarray]) -> list[list[Candidate]]:
        if not frames:
            return []
        h, w = frames[0].shape[:2]
        s, x0, y0 = letterbox(w, h, self.W, self.H)
        out: list[list[Candidate]] = []
        for st in range(0, len(frames), self.FRAMES):
            win = frames[st:st + self.FRAMES]
            x = [self.prep(f) for f in win]
            x = x + [x[-1]] * (self.FRAMES - len(x))
            hm = self.session.run(None, {self.input: np.concatenate(x)[None].astype(np.float32)})[0][0]
            for m in hm[:len(win)]:
                out.append(merge([Candidate((bx - x0) / s, (by - y0) / s, p) for bx, by, p in blobs(m, self.threshold)],
                                 self.merge_px))
        return out


DETECTORS = ["v4c", "v4c-tiles", "ravel011", "ravel012", "wasb"]


def load(name: str):
    """A detector by name: v4c (whole frame), v4c-tiles (+ 2 x 2 tiles), ravel011, ravel012, wasb."""
    if name == "v4c":
        return VballNet(BALL_MODELS["v4c"])
    if name == "v4c-tiles":
        return VballNet(BALL_MODELS["v4c"], grid=(2, 2))
    if name in ("ravel011", "ravel012"):
        return Ravel(BALL_MODELS[name])
    if name == "wasb":
        return Wasb(BALL_MODELS["wasb"])
    raise ValueError(f"unknown ball detector {name!r}; one of {DETECTORS}")
