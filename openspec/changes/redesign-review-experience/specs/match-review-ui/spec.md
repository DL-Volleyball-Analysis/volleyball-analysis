## MODIFIED Requirements

### Requirement: Add videos from the library
Every page SHALL offer an "Add match video" action in the header, and the library SHALL show a drop area as its first
card; the user SHALL be able to add videos by dropping files or choosing them with a file picker, SHALL see upload
progress per file, and SHALL see an error naming the file and the reason when a file is rejected.

#### Scenario: Drop a video
- **WHEN** the user drops match.mp4 on the library
- **THEN** a card for match.mp4 appears with its upload progress and then its analysis queued

#### Scenario: Upload from a match page
- **WHEN** the user is on a match page and chooses "Add match video"
- **THEN** a file picker opens and the chosen file is added to the library

#### Scenario: Drop an unsupported file
- **WHEN** the user drops notes.txt
- **THEN** the library shows that notes.txt is not a supported video type and no card is added

### Requirement: Video overlays
The match page SHALL overlay on the video the ball trail of the last 0.5 s, the player boxes with shirt numbers, and,
when a court mapping exists, the court lines; overlays whose result exists SHALL be on when the page opens, each SHALL
be switchable from chips on the video, and overlays SHALL stay aligned with the video at any player size.

#### Scenario: Resize
- **WHEN** the window is resized while paused
- **THEN** the ball trail is still drawn on the ball

#### Scenario: Defaults
- **WHEN** the user opens a video with a ball track and player tracks but no court mapping
- **THEN** the ball and player overlays are on and the court chip is disabled with the reason

### Requirement: Demo data is labelled
Whenever any rally shown comes from demo data, the match page SHALL say in plain language that these rallies are
examples and not results of the analysis, without internal terms such as milestones or stage versions.

#### Scenario: Demo video
- **WHEN** the user opens a video with demo rallies
- **THEN** a notice says the rallies are examples, not analysis results

### Requirement: Stage status
The match page SHALL show an analysis health panel as the first inspector tab listing ball, court, players, shirt
numbers, actions, 3D flights and rallies, each as found, partly found, needs the user, or unavailable, with the
reason in plain language and, where a user action fixes it, a button for that action.

#### Scenario: Court needs confirmation
- **WHEN** a court shot needs review
- **THEN** the panel says the court needs confirmation in that shot and offers "Set court", which opens the court picker on that shot

#### Scenario: Court model missing
- **WHEN** the court stage is unavailable
- **THEN** the panel shows the court as unavailable with the reason

#### Scenario: 3D missing
- **WHEN** no shot has a usable court
- **THEN** the panel shows 3D flights as unavailable because the court is not set, with the same "Set court" action

## ADDED Requirements

### Requirement: Match cards in the library
The library SHALL show each video as a card with a thumbnail, its display name, duration, upload date, analysis state
(queued, analysing with the current stage and progress, needs you, done, failed) and its result summary.

#### Scenario: Analysis running
- **WHEN** a video is in its players stage
- **THEN** its card shows "Analysing: players" with the progress

#### Scenario: Rallies could not be told
- **WHEN** the rallies stage is unavailable for a video
- **THEN** its card says rallies could not be told on this footage instead of "No rallies yet"

### Requirement: Readable timeline
The timeline SHALL draw each event lane as a density strip coloured by event type, SHALL show text labels only when
zoomed in far enough that labels do not overlap, and SHALL support zoom and pan.

#### Scenario: Long clip
- **WHEN** a 2.5-minute video with 300 action events is shown at full width
- **THEN** no two labels overlap

### Requirement: Score only with rallies
The scoreboard SHALL be shown only when the video has rallies.

#### Scenario: No rallies
- **WHEN** a video has no rallies
- **THEN** no score is shown and the rally panel explains why there are none
