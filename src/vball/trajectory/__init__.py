"""Single-camera 3D ball trajectories: flights between touches, ballistic fit, derived values.

Between two touches the ball flies ballistically: p(t) = p0 + v0 t + 1/2 g t^2, g = (0, 0, -9.81) in
the court frame (metres, z up; see court.py). Given a calibrated camera (`vball.calibration`), each
flight's six unknowns (p0, v0) are fitted to the 2D detections by minimising reprojection error with a
robust loss. The fit gives 3D positions for every frame of the flight, including frames where the ball
was not detected, plus landing point, net-crossing height, start speed and apex.

Every flight carries its fit error (median residual, pixels) and depth conditioning: the standard
deviation of the position along the camera ray, from the fit's Jacobian. A flight above either
threshold is low quality, with the reason, and the UI must show it as uncertain.

Air drag and spin are not modelled (see the change's design for the optional drag comparison).
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from ..calibration import Camera
from ..court import NET_X

G = np.array([0.0, 0.0, -9.81])
BALL_RADIUS = 0.105  # m; the ball touches the floor when its centre is this high


@dataclass
class FlightConfig:
    # touch detection, tuned on synthetic 1080p / 50 fps rallies with 2 px noise: interior velocity
    # jumps stay below ~5 px/frame with an 8-frame window, touches are above ~13 px/frame. Touches
    # closer than ~2 windows apart (0.3 s at 50 fps) are not separated.
    window: int = 8            # frames on each side for the image velocity at a candidate cut
    min_jump_px: float = 8.0   # velocity change (px/frame) that marks a touch ...
    rel_jump: float = 0.5      # ... and at least this fraction of the speed
    max_gap: int = 6           # missing frames that end a flight
    min_detections: int = 8    # shorter flights are not reconstructed
    max_fit_px: float = 4.0    # quality: median reprojection residual
    # physically impossible flights are dropped, not drawn as "low quality": a dashed line through the
    # stands still misleads. Fastest recorded spikes and serves are about 35 m/s.
    max_speed_mps: float = 40.0
    hall_margin_m: float = 10.0  # beyond the court on every side
    max_height_m: float = 20.0
    max_depth_sd_m: float = 0.5  # quality: position sd along the camera ray (mid-flight)


@dataclass
class Flight:
    start: int  # first frame (inclusive)
    end: int    # last frame (inclusive)


@dataclass
class FlightFit:
    start: int
    end: int
    p0: np.ndarray                 # position at the start frame (m)
    v0: np.ndarray                 # velocity at the start frame (m/s)
    fps: float
    fit_px: float                  # median reprojection residual
    depth_sd_m: float              # sd of the mid-flight position along the camera ray
    quality: str = "ok"            # "ok" | "low"
    reasons: list[str] = field(default_factory=list)

    def at(self, frames) -> np.ndarray:
        t = (np.asarray(frames, float) - self.start) / self.fps
        return self.p0 + np.outer(t, self.v0) + 0.5 * np.outer(t * t, G)

    def derived(self) -> dict:
        """Landing point, net crossing, start speed and apex, where they apply (None otherwise)."""
        T = (self.end - self.start) / self.fps
        a = 0.5 * G[2]
        out = {"start_speed_mps": float(np.linalg.norm(self.v0)), "apex": None, "net_crossing": None,
               "landing": None, "quality": self.quality}
        t_apex = -self.v0[2] / G[2]
        if 0 < t_apex < T:
            out["apex"] = {"t": float(t_apex), "height_m": float(self.p0[2] + self.v0[2] * t_apex + a * t_apex ** 2)}
        if abs(self.v0[0]) > 1e-9:
            t_net = (NET_X - self.p0[0]) / self.v0[0]
            if 0 <= t_net <= T:
                p = self.p0 + self.v0 * t_net + 0.5 * G * t_net ** 2
                out["net_crossing"] = {"t": float(t_net), "height_m": float(p[2]), "y_m": float(p[1])}
        # floor contact: later root of z(t) = BALL_RADIUS; reported when the flight ends there
        disc = self.v0[2] ** 2 - 4 * a * (self.p0[2] - BALL_RADIUS)
        if disc >= 0:
            t_land = (-self.v0[2] - np.sqrt(disc)) / (2 * a)
            if 0 < t_land <= T + 3 / self.fps:
                p = self.p0 + self.v0 * t_land + 0.5 * G * t_land ** 2
                out["landing"] = {"t": float(t_land), "x_m": float(p[0]), "y_m": float(p[1])}
        return out


def _end_velocity(frames: np.ndarray, pts: np.ndarray, at: int) -> np.ndarray:
    """Image velocity (px/frame) at frame `at` from a quadratic fitted to the points."""
    t = frames - at
    coef = np.polyfit(t, pts, 2)  # rows: t^2, t, 1 for u and v
    return coef[1]


def segment(uv: np.ndarray, cfg: FlightConfig = FlightConfig()) -> list[Flight]:
    """Split an image track (N, 2), NaN rows for misses, into flights between touches."""
    uv = np.asarray(uv, float)
    seen = ~np.isnan(uv).any(axis=1)
    idx = np.flatnonzero(seen)
    if len(idx) == 0:
        return []
    # runs of detections separated by gaps longer than max_gap
    runs, cur = [], [idx[0]]
    for a, b in zip(idx, idx[1:]):
        if b - a - 1 > cfg.max_gap:
            runs.append(cur)
            cur = []
        cur.append(b)
    runs.append(cur)

    k = cfg.window
    flights = []
    for run in runs:
        run = np.array(run)
        pts = uv[run]
        score = np.zeros(len(run))
        for i in range(k, len(run) - k):
            # velocity at frame i extrapolated from a quadratic on each side: continuous along a
            # ballistic arc (also at the apex, where the image direction reverses), broken at a touch
            vb = _end_velocity(run[i - k:i + 1], pts[i - k:i + 1], run[i])
            va = _end_velocity(run[i:i + k + 1], pts[i:i + k + 1], run[i])
            jump = np.linalg.norm(va - vb)
            speed = max(np.linalg.norm(va), np.linalg.norm(vb))
            if jump > max(cfg.min_jump_px, cfg.rel_jump * speed):
                score[i] = jump
        # one cut per touch: the strongest frame of each group of candidate frames
        cuts, i = [], 0
        while i < len(run):
            if score[i] > 0:
                j = i
                while j + 1 < len(run) and score[j + 1] > 0:
                    j += 1
                cuts.append(i + int(np.argmax(score[i:j + 1])))
                i = j + 1
            else:
                i += 1
        # cuts closer than one window belong to the same touch: keep the strongest
        merged = []
        for c in cuts:
            if merged and run[c] - run[merged[-1]] < k:
                if score[c] > score[merged[-1]]:
                    merged[-1] = c
            else:
                merged.append(c)
        bounds = [0] + merged + [len(run) - 1]
        for a, b in zip(bounds, bounds[1:]):
            if b - a + 1 >= cfg.min_detections:
                flights.append(Flight(int(run[a]), int(run[b])))
    return flights


def _project(cam: Camera, params: np.ndarray, t: np.ndarray) -> np.ndarray:
    p0, v0 = params[:3], params[3:]
    return cam.project(p0 + np.outer(t, v0) + 0.5 * np.outer(t * t, G))


def _point_on_ray_at_height(cam: Camera, uv: np.ndarray, z: float) -> np.ndarray | None:
    d, c = cam.ray(uv), cam.position
    if abs(d[2]) < 1e-6:
        return None
    s = (z - c[2]) / d[2]
    return c + s * d if s > 0 else None


def fit(cam: Camera, uv: np.ndarray, flight: Flight, fps: float,
        cfg: FlightConfig = FlightConfig()) -> FlightFit:
    """Ballistic fit of one flight. uv: the whole track (N, 2) with NaN rows for misses."""
    frames = np.arange(flight.start, flight.end + 1)
    obs = uv[frames]
    seen = ~np.isnan(obs).any(axis=1)
    t, obs = (frames[seen] - flight.start) / fps, obs[seen]
    T = (flight.end - flight.start) / fps

    def residuals(x):
        return (_project(cam, x, t) - obs).ravel()

    best = None
    for z0 in (1.0, 2.0, 3.0):
        for z1 in (1.0, 2.0, 3.0):
            a = _point_on_ray_at_height(cam, obs[0], z0)
            b = _point_on_ray_at_height(cam, obs[-1], z1)
            if a is None or b is None or t[-1] <= 0:
                continue
            v0 = (b - a - 0.5 * G * t[-1] ** 2) / t[-1]
            sol = least_squares(residuals, np.concatenate([a, v0]), loss="huber", f_scale=2.0)
            if best is None or sol.cost < best.cost:
                best = sol
    if best is None:
        raise ValueError("no initialisation: rays do not reach the start heights")

    res = np.linalg.norm(best.fun.reshape(-1, 2), axis=1)
    fit_px = float(np.median(res))
    # depth conditioning: covariance of (p0, v0) from the Jacobian, propagated to mid-flight and onto
    # the camera ray through that point; noise level from the residuals (at least 1 px)
    sigma = max(1.0, 1.4826 * float(np.median(res)))
    JtJ = best.jac.T @ best.jac
    cov = sigma ** 2 * np.linalg.pinv(JtJ)
    tm = T / 2
    A = np.hstack([np.eye(3), tm * np.eye(3)])
    p_mid = best.x[:3] + best.x[3:] * tm + 0.5 * G * tm ** 2
    d = p_mid - cam.position
    d /= np.linalg.norm(d)
    depth_sd = float(np.sqrt(max(d @ A @ cov @ A.T @ d, 0.0)))

    reasons = []
    if fit_px > cfg.max_fit_px:
        reasons.append(f"fit error {fit_px:.1f} px")
    if depth_sd > cfg.max_depth_sd_m:
        reasons.append("depth poorly constrained")
    return FlightFit(flight.start, flight.end, best.x[:3], best.x[3:], fps, fit_px, depth_sd,
                     "low" if reasons else "ok", reasons)


def implausible(f: "FlightFit", positions: np.ndarray, cfg: FlightConfig = FlightConfig()) -> str | None:
    """Why a fitted flight cannot be a volleyball flight, or None. (Low quality is about uncertainty; this is
    about impossibility: a wrong camera or false detections can fit a path through the stands.)"""
    from ..court import LENGTH, WIDTH
    if np.linalg.norm(f.v0) > cfg.max_speed_mps:
        return f"start speed {np.linalg.norm(f.v0):.0f} m/s"
    m = cfg.hall_margin_m
    x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
    if (x < -m).any() or (x > LENGTH + m).any() or (y < -m).any() or (y > WIDTH + m).any():
        return "path leaves the hall"
    if (z < -0.5).any() or (z > cfg.max_height_m).any():
        return "path below the floor or too high"
    return None


def reconstruct(cam: Camera, uv: np.ndarray, fps: float, cfg: FlightConfig = FlightConfig(),
                rejected: list | None = None) -> list[dict]:
    """Segment a track and fit every flight. Each item: the fit, positions for every frame of the
    flight with an observed flag, and the derived values. Physically impossible fits are left out; when a
    list is passed as `rejected`, their (start, end, reason) are appended to it."""
    uv = np.asarray(uv, float)
    out = []
    for fl in segment(uv, cfg):
        try:
            f = fit(cam, uv, fl, fps, cfg)
        except ValueError as e:  # no starting point (a camera whose rays miss the court heights)
            if rejected is not None:
                rejected.append((fl.start, fl.end, str(e)))
            continue
        frames = np.arange(fl.start, fl.end + 1)
        positions = f.at(frames)
        why = implausible(f, positions, cfg)
        if why:
            if rejected is not None:
                rejected.append((fl.start, fl.end, why))
            continue
        out.append({"fit": f, "frames": frames, "positions": positions,
                    "observed": ~np.isnan(uv[frames]).any(axis=1), "derived": f.derived()})
    return out
