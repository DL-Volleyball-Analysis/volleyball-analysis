## ADDED Requirements

### Requirement: Database backups
The system SHALL keep rolling, consistent backups of the app database: one when the API or the worker starts and at
most one per hour after finished jobs, keeping the newest 10, and SHALL restore a chosen backup only after backing up
the current database.

#### Scenario: Start
- **WHEN** the worker starts
- **THEN** a new backup file with all current rows exists in the backups folder, and older files beyond the newest 10
  are removed

#### Scenario: Restore
- **WHEN** the user restores a backup
- **THEN** the database holds that backup's rows, and the database as it was before is itself saved as a backup
