# Design

## Decisions

**CVAT, not our own tool.** CVAT (self-hosted, Docker) covers players, court keypoints, ball points and actions, with
interpolation and pre-annotation import. Label Studio is weaker on video tracks; X-AnyLabeling is image-first; the
TrackNet tool labels only the ball (kept as a fallback for long ball-only sessions); Roboflow is cloud-only and slow
from here.

**Formats.** Players: MOT 1.1 (tracks, ids). Court: CVAT for images 1.1 with a 14-point skeleton whose point order is
`vball.court_keypoints`' order. Ball: one point track per video, `outside` where not visible. Actions: a track
attribute changing per frame. All through CVAT's XML export, parsed by our converter.

**Labels only where touched.** Pre-annotations are imported marked as predictions (a `source=model` attribute); the
labeller's edit or explicit acceptance sets `source=human`; the export keeps only `source=human`, so unseen errors do
not become labels.

**Partial labels, split by video.** A frame may be labelled for any subset of tasks; whole videos go to train,
validation or test, the test videos fixed once chosen.

**Correctness of our converters.** Round trip on SportsMOT ground truth (TrackEval must give 1.0, as the existing
ground-truth-as-tracker check); overlay sheets of sampled frames inspected after each export; unit tests for the
point order, frame offsets and the outside flag.

## Risks
Anchoring on the model's prediction: a small subset of frames is labelled from scratch to measure the bias. CVAT needs
about 4-8 GB of memory in Docker.
