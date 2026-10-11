# Design

## Context

- Pipeline stages run in order with per-stage caching (`openspec/specs/analysis-jobs`); ball tracking already serves windowed data to the web app the same way players will be served.
- Court mappings come from `add-court-registration` (`vball.court_registration.mapping_at`); until that lands, this stage runs without filtering or positions.
- The local machine is an M1 Pro CPU; the court model (YOLO26n-pose, 960 px) measured ~89 ms per image there.
- SportsMOT annotates on-court players only, in broadcast footage; our own footage is a tripod in a gym.

## Goals / Non-Goals

**Goals:**
- A measured baseline before any training; training only when the baseline misses the PRD targets.
- Detection and tracking independent of the court model, so they can be evaluated and used now.

**Non-Goals:**
- Re-identification across rallies or cuts, jersey numbers, poses.

## Decisions

### Module ownership
| Responsibility | Module |
|---|---|
| Detect + track people in a video, interpolate between sampled frames | new `vball.players` |
| On-court filter, court position, side of net | `vball.players`, using `vball.court` and the court mapping |
| Tracking metrics on labelled sequences | new `scripts/eval_player_tracking.py` |
| Stage wiring, `players.csv.gz`, API window endpoint | web app `pipeline.py`, `main.py` |
| Overlay layer and toggle | web app `OverlayCanvas`, `LayerMenu` |

### Detector and tracker: pretrained first
YOLO26 person class (COCO weights via ultralytics) with ultralytics' tracker. Compare BoT-SORT (has camera-motion compensation, which helps panning broadcast shots) with ByteTrack (simpler, faster), and nano vs small detector, at 960 and 1280 px input: far-side players in a wide shot are small. The evaluation picks the default; the choice is configuration, not spec.
*Alternative:* keep the capstone's YOLOv8 + Norfair. Rejected as the starting point because it was never measured either and Norfair needs its own tuning; it can be added to the comparison if the new baseline is weak.

### Reduced detection rate with interpolation
Detect and track at a configurable rate (default 10 fps) and interpolate each track's box linearly between samples for overlays and positions. At ~90 ms per frame, every frame of a 2-hour 30 fps match would take ~5 hours on this CPU; 10 fps is ~1.8 hours, still over the PRD's 1-hour budget, so the evaluation also measures 5 fps and the effect of the rate on IDF1. If no CPU rate meets both accuracy and time, the stage gets a Colab path (same module, GPU) rather than a lower accuracy target.

### On-court filter
Map the box's bottom-centre through the frame's court mapping; keep it when inside the court plus margins (3 m beyond the sidelines, 7 m behind the end lines, where servers stand). Margins are configuration. Side of net: `vball.court.side_of_net(x)`. Teams (A/B) are not assigned here: which team is on which side per set belongs to rally scoring.

### Storage and API
`players.csv.gz`: frame, track_id, x1, y1, x2, y2, conf, court_x, court_y, side, on_court, interpolated. A 2-hour match is ~1 M rows; gzip keeps it small and pandas reads it directly. `GET /videos/{id}/players?start=&end=` returns rows in a time window, like the ball endpoint.

### Evaluation
TrackEval (the reference implementation of HOTA), cloned unmodified into `external/`, run by `scripts/eval_player_tracking.py` on SportsMOT volleyball validation sequences converted to MOTChallenge format (SportsMOT already uses it). The script prints per-sequence and overall HOTA, IDF1, MOTA, detection recall and precision, plus model, tracker, input size and detection fps.

### Fine-tuning (conditional)
If the baseline misses the targets: a Colab notebook fine-tunes the detector on SportsMOT volleyball training sequences (person boxes only), with checkpoints on Drive and resume, like the court notebook. Re-run the same evaluation; report both numbers.

## Risks / Trade-offs

- [SportsMOT is broadcast footage; ours is a gym tripod] → Report SportsMOT and own-footage numbers separately; own labels come with M5.
- [CC BY-NC 4.0] → Research use only; the dataset is not redistributed or committed; a commercial use would need other data.
- [ID switches at the net, where players overlap] → Measured by IDF1; rally-scoped ids limit the damage; re-id is a later change.
- [CPU time] → Reduced rate, measured; Colab path if needed.

## Migration Plan

New stage; existing videos run it on their next analysis. Stage order changes (players before events), so the events stage version is bumped and recomputed after players.
