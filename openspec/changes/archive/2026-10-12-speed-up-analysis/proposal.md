# Proposal

## Why
Analysis takes 23-26 minutes per 3-minute fixed-camera clip; the court, 3D and rallies stages repeat work for still
cameras and out-of-training footage (PRD docs/prd/analysis-speed.md).

## What Changes
- Court stage: shots whose camera is still (camera motion) get keypoint samples at 1 per second instead of 5.
- Trajectory stage: one calibration per still shot, shared by its flights.
- Rallies stage: `vball.rally_cues.quick_check` on 30 frames spread over the video (court model and player detector
  only); when it is out of training the stage returns unavailable without extracting the full cues.
- Measured: stage times on fixed_hawaii_irvine before and after, results unchanged.

## Capabilities

### Modified Capabilities
- `analysis-jobs`: stage work scales with what the footage needs.

## Impact
`webapp/backend/pipeline.py` (court, trajectory, rallies; version bumps), `src/vball/court_registration.py` (sample
rate per shot), `src/vball/rally_cues.py` (quick check), tests.
