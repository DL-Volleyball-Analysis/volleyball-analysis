# video-library Specification

## Purpose

Keeps the set of match videos the user analyses: adding, listing, playing and removing them.

## Requirements

### Requirement: Add videos
The system SHALL accept video uploads with extensions mp4, mov, avi, mkv or m4v, read their metadata (fps, frame count, size), and queue a full analysis immediately.

#### Scenario: Upload a match
- **WHEN** the user uploads match.mp4
- **THEN** the video appears in the list with its metadata and a queued analysis job

#### Scenario: Unsupported or unreadable file
- **WHEN** the user uploads a .txt file or a file that cannot be decoded
- **THEN** the upload is rejected with an error and nothing is stored

### Requirement: Register local files
The system SHALL register a video that already exists on this machine by path, without copying it.

#### Scenario: Import a local clip
- **WHEN** a local video path is registered
- **THEN** the video is listed and analysed from its original location

### Requirement: Play with seeking
The system SHALL serve a video's file with byte-range support so players can seek.

#### Scenario: Range request
- **WHEN** a client requests bytes 0-99 of a video
- **THEN** it receives a partial-content response of exactly 100 bytes

### Requirement: Remove videos
Deleting a video SHALL remove its record, jobs, rallies and analysis results, and its file only if the file was uploaded (never an imported original).

#### Scenario: Delete an imported clip
- **WHEN** a video registered from a local path is deleted
- **THEN** its record and results are gone and the original file still exists

### Requirement: Score summary in the video list
Each video returned by the list and detail endpoints SHALL include a score summary taken from its last rally: sets won by each team, the current set number and both teams' points in it, the number of rallies, how many are corrected, and whether any rally is demo data; a video without rallies SHALL have no summary.

#### Scenario: Analysed video
- **WHEN** a video's last rally leaves sets at 1-0 and the second set at 12-10
- **THEN** its list entry shows sets 1-0, set 2, points 12-10

#### Scenario: No rallies yet
- **WHEN** a video has not been analysed
- **THEN** its list entry has no score summary
