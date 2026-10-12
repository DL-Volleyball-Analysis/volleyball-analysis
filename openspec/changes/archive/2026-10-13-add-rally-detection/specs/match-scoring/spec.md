# Spec Delta

## ADDED Requirements

### Requirement: Detected rallies
The rallies stage SHALL segment a video into rallies, each with a start time, an end time and a confidence, from
cues the analysis already computes, and SHALL keep showing demo rallies, labelled as such, when no detector result
is available.

#### Scenario: Close-up between rallies
- **WHEN** the broadcast cuts to a close-up of a player between two rallies
- **THEN** no rally is open during the close-up

#### Scenario: Short false start
- **WHEN** the cues indicate play for less than the minimum rally length
- **THEN** no rally is created

### Requirement: Rally detection measured
The project SHALL report rally detection on held-out labelled matches: the share of labelled rallies matched by a
detected one, the share of detected rallies that match a labelled one, and the median start and end error in seconds.

#### Scenario: Running the rally evaluation
- **WHEN** the evaluation runs on the held-out matches
- **THEN** it prints matched-rally precision and recall and the median boundary errors per method
