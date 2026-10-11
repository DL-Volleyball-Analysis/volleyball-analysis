# Spec Delta

## ADDED Requirements

### Requirement: Ball model measured on broadcast and gym footage
The project SHALL report the pipeline's ball model on held-out labelled matches of both broadcast and amateur gym
footage, beside the previous model, with the same metric, and SHALL switch the pipeline's ball model only when the new
one is better on both.

#### Scenario: Comparing ball models
- **WHEN** a newly trained ball model is evaluated
- **THEN** precision, recall and F1 at 4 and 10 pixels are reported for it and for the current model on the broadcast test matches and on the held-out gym matches

#### Scenario: A model that is better on one footage only
- **WHEN** the new model wins on broadcast but loses on gym matches
- **THEN** the pipeline keeps the current model and the result is recorded
