## ADDED Requirements

### Requirement: Ball model by footage type
The ball stage SHALL use the gym ball model (WASB gym weights) when every camera shot of the video is still, and the
default model (VballNet V4c) otherwise or when the gym weights are not installed, reporting the model and the reason.

#### Scenario: Fixed phone camera in a gym
- **WHEN** a still-camera video is analysed
- **THEN** the ball stage uses the gym model and its result names it

#### Scenario: Broadcast clip
- **WHEN** a panning broadcast clip is analysed
- **THEN** the ball stage uses VballNet V4c
