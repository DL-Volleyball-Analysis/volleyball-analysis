## ADDED Requirements

### Requirement: Ball model by footage type
When the gym ball option is switched on, the ball stage SHALL use the gym ball model (WASB gym weights) when every
camera shot of the video is still, and the default model (VballNet V4c) otherwise or when the gym weights are not
installed; with the option off (the default) it SHALL use the default model. It SHALL report the model and the reason.

#### Scenario: Fixed phone camera in a gym
- **WHEN** a still-camera video is analysed with the gym ball option on
- **THEN** the ball stage uses the gym model and its result names it

#### Scenario: Option off
- **WHEN** a still-camera video is analysed with the gym ball option off
- **THEN** the ball stage uses VballNet V4c with the reason "default model"

#### Scenario: Broadcast clip
- **WHEN** a panning broadcast clip is analysed
- **THEN** the ball stage uses VballNet V4c
