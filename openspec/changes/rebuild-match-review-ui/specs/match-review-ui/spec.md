# Spec Delta

## Purpose

Defines what the user sees and does in the browser to add match videos, follow their analysis and review a match rally by rally.

## ADDED Requirements

### Requirement: Add videos from the library
The library SHALL let the user add videos by dragging files onto the page or choosing them with a file picker, and SHALL show an error naming the file and the reason when a file is rejected.

#### Scenario: Drop a video
- **WHEN** the user drops match.mp4 on the library
- **THEN** the video appears in the list with its analysis queued

#### Scenario: Drop an unsupported file
- **WHEN** the user drops notes.txt
- **THEN** the library shows that notes.txt is not a supported video type and the list is unchanged

### Requirement: Live analysis progress
Each video in the library SHALL show its analysis state, current stage and percentage, updated live while the analysis runs without reloading the page.

#### Scenario: Analysis running
- **WHEN** a video's analysis moves from the decode stage to the ball stage
- **THEN** its row shows the ball stage and the new percentage within about a second

### Requirement: Failed analysis
A video whose analysis failed SHALL show the error reason and an action that starts the analysis again.

#### Scenario: Retry
- **WHEN** the user chooses to analyse a failed video again
- **THEN** a new analysis is queued and the row shows it as queued

### Requirement: Score at a glance
Each analysed video in the library SHALL show its current score summary, and SHALL mark it as demo when it comes from demo rallies.

#### Scenario: Demo rallies
- **WHEN** a video's rallies are demo data
- **THEN** its score summary is labelled as demo

### Requirement: Scoreboard follows playback
The match page SHALL show the set number, the points of both teams in that set and the sets won, for the rally at the current playback position (or the last finished rally before it).

#### Scenario: Seeking
- **WHEN** the user seeks into rally 20
- **THEN** the scoreboard shows the score after rally 20

### Requirement: Rally list
The match page SHALL list every rally with its number, winner, end reason and confidence, highlight the rally at the playback position, mark low-confidence rallies, and mark rallies the user corrected.

#### Scenario: Low confidence
- **WHEN** a rally's confidence is below the review threshold
- **THEN** the rally is marked as needing review in the list and on the timeline

### Requirement: Jump to a rally
Selecting a rally in the list or on the rally timeline SHALL move playback to the start of that rally; any rally of a video SHALL be reachable from the library in at most two selections.

#### Scenario: From the library
- **WHEN** the user opens a video from the library and selects rally 12
- **THEN** playback is at the start of rally 12

### Requirement: Keyboard review
The match page SHALL support: J / K previous / next rally, Space play / pause, 1 / 2 set the current rally's winner to team A / B, 0 clear the correction. Shortcuts SHALL NOT fire while typing in a text field.

#### Scenario: Correct with the keyboard
- **WHEN** rally 7 is current and the user presses 2
- **THEN** rally 7's winner becomes team B, it is marked corrected, and the scoreboard and later scores update

### Requirement: Court map
The match page SHALL draw the 18 m × 9 m court to scale with its lines and plot each rally's landing point, using different marker shapes for in and out, and SHALL highlight the current rally's landing.

#### Scenario: Out ball
- **WHEN** a rally ended with the ball landing out
- **THEN** its landing is drawn outside the court lines with the out marker

### Requirement: Video overlays
The match page SHALL overlay on the video the ball trail of the last 0.5 s and, when a court mapping exists, the court lines; each overlay SHALL be switchable on and off, and overlays SHALL stay aligned with the video at any player size.

#### Scenario: Resize
- **WHEN** the window is resized while paused
- **THEN** the ball trail is still drawn on the ball

### Requirement: Demo data is labelled
Whenever any rally shown comes from demo data, the match page SHALL display a notice that the rallies are demo data and not analysis results.

#### Scenario: Demo video
- **WHEN** the user opens a video with demo rallies
- **THEN** a demo notice is visible above the scoreboard

### Requirement: Stage status
The match page SHALL show every analysis stage with its status (done, not available yet, not implemented yet, pending) and its message.

#### Scenario: Court model missing
- **WHEN** the court stage is unavailable
- **THEN** the panel shows the court stage as not available yet with the reason

### Requirement: Smooth playback
During playback, page content other than the video overlays SHALL update at most 5 times per second.

#### Scenario: Profiling playback
- **WHEN** a match plays for 10 seconds with the profiler recording
- **THEN** at most 50 UI commits are recorded outside the overlay canvas

### Requirement: Accessible on desktop and phone
Pages SHALL work from 360 px wide to desktop, be fully usable by keyboard with visible focus, respect the reduced-motion setting, support light and dark themes, and never use colour as the only way to tell teams or in/out apart.

#### Scenario: Phone width
- **WHEN** the match page is opened at 360 px wide
- **THEN** video, scoreboard and a tab switcher for rallies, court and stages are stacked without horizontal scrolling
