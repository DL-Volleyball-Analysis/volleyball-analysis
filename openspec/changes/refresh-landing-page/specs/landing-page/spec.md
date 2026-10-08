# Spec Delta

## Purpose

Defines what the public landing page may claim about the system and what it shows, so the site stays truthful as the system evolves.

## ADDED Requirements

### Requirement: Evidence for every number
Every quantitative claim on the page SHALL name its source (evaluation script output, benchmark or paper) via a link or footnote, and SHALL state whether it is a labelled accuracy or a label-free proxy; numbers without a source SHALL NOT be shown.

#### Scenario: Unmeasured accuracy
- **WHEN** no labelled evaluation exists for a metric
- **THEN** the page does not show a value for it

#### Scenario: Proxy metric
- **WHEN** the page shows ball detection rate on broadcast clips
- **THEN** it is labelled as a detection rate without labels, not as accuracy

### Requirement: Features match the system
Each feature described SHALL be either available in the current web app or marked as in progress with its milestone.

#### Scenario: Planned feature
- **WHEN** automatic scoring is not yet implemented
- **THEN** its feature card says it is in progress (milestone M3)

### Requirement: Research section
The page SHALL include a section for researchers that links the PRD, the OpenSpec specifications and the source repositories, and summarises the technical approach.

#### Scenario: Reviewer looks for code
- **WHEN** a reviewer opens the research section
- **THEN** they find links to the analysis repository, the web app repository and the specifications

### Requirement: Bilingual content
All page text SHALL be available in English and Traditional Chinese, switchable on the page.

#### Scenario: Switch language
- **WHEN** the visitor switches to Traditional Chinese
- **THEN** every section, including the research section and stat sources, is shown in Traditional Chinese

### Requirement: Light initial load
The initial page load SHALL stay under 2 MB excluding the demo video, and the demo video SHALL load only when it is about to be visible.

#### Scenario: Visitor on a phone
- **WHEN** the page loads on a mobile connection without scrolling
- **THEN** the demo video file is not downloaded until the visitor reaches it
