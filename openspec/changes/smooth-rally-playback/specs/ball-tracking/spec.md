## ADDED Requirements

### Requirement: Ball model by footage type
The ball stage SHALL use the gym ball model (WASB gym weights) for still cameras and for shots whose court is
registered by the gym court model or a correction, and SHALL use the default model (VballNet V4c) for broadcast
footage, reporting which model it used.

#### Scenario: Fixed phone camera in a gym
- **WHEN** a still-camera video is analysed
- **THEN** the ball stage uses the gym model and its result names it

#### Scenario: Broadcast clip
- **WHEN** a panning broadcast clip is analysed
- **THEN** the ball stage uses VballNet V4c
