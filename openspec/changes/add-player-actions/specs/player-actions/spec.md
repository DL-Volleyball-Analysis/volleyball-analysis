# Spec Delta

## Purpose

Says what each tracked player does (serve, receive, set, spike, block) and which shirt number they wear, with
the accuracy of both measured on held-out data.

## ADDED Requirements

### Requirement: Measured models
The project SHALL report the action model's mAP@0.5 per class and the number model's digit mAP@0.5 and
whole-number accuracy on test splits that took no part in training or model selection, and the actions stage
SHALL NOT be enabled by default before these numbers are recorded.

#### Scenario: Evaluation
- **WHEN** the evaluation scripts run with the installed models
- **THEN** they print the per-class and overall test numbers and the split sizes

### Requirement: Action events
The system SHALL detect actions on sampled frames, assign each detection to the player track whose box overlaps
it most (none below a minimum overlap), and merge consecutive detections of one action by one track into an
event with player, action, start, end and peak confidence.

#### Scenario: A spike
- **WHEN** a tracked player is detected spiking on several consecutive samples
- **THEN** one spike event is reported for that player's track, from the first to the last of those samples

#### Scenario: Detection without a player
- **WHEN** an action box overlaps no tracked player
- **THEN** the event is reported without a player

### Requirement: Shirt numbers
For each track the system SHALL detect digits inside the player's box on sampled frames, compose them left to
right into a number per frame, and report the most frequent number with the share of frames that agree; a track
whose share is below the configured threshold, or with too few readings, SHALL have no number.

#### Scenario: Two-digit number
- **WHEN** the digits 1 and 0 are detected side by side on a player's back
- **THEN** that frame's reading is 10

#### Scenario: Unclear vote
- **WHEN** a track's readings disagree (no number reaches the threshold share)
- **THEN** the track has no number and is shown by its tracking id

### Requirement: Display
Players with a number SHALL be labelled with it (on the video, the court map and the rendered video) and others
with their tracking id marked as such; action events SHALL appear on the match timeline and in the rendered video.

#### Scenario: Labels
- **WHEN** a track has number 7 and another has none
- **THEN** the first is labelled #7 and the second ID followed by its tracking id
