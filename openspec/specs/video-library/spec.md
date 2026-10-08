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
