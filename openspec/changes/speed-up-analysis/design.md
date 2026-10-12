# Design

## Court
`court_registration.sample_frames` already takes a rate. The court stage decides per shot before detection: still
(`court_registration.still`, from the decode stage's camera motion) -> STILL_SAMPLE_FPS = 1, else SAMPLE_FPS = 5.
`register_shot` takes the rate. The line evidence later fills every 5 Hz frame for line fits, so the samples later
stages read keep their density.

## 3D
The per-flight camera key is the flight's middle frame only when the shot is not still; a still shot uses one key, so
its camera is calibrated once.

## Rallies
`quick_check(video, n=30)`: n frames spread over the video (seeking), the court keypoint model and the player detector
of the cues on each; returns a cues frame with court_conf, court_ok and players (motion and ball columns 0), which
`rallies.outside_training` reads. Out of training -> unavailable at once; otherwise the full cues as before.

## Risk
A shot judged still that slowly zooms: the threshold (centre moves under 1% of the width over the shot) keeps such
shots at 5 Hz.
