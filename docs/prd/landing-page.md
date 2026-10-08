# PRD: Landing page (volleyvision-website)

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/refresh-landing-page/` · Repo plan: [`docs/repo-organization.md`](../repo-organization.md)

## Problem
The landing page describes the capstone system and makes claims nobody measured: "98.5% detection accuracy", "100K+ frames analyzed", "automatic court detection" (the capstone court was four manual clicks). Grad-school reviewers and coaches who try the system will notice the gap. It also ships 66 MB of video and dozens of unused components.

## Audience and job
- Professors and admission reviewers (primary now): understand in one minute what the system does, what is novel, how well it works, and where the code is.
- Coaches: see what they get (score, rallies, landing map) and how to try it.

## Requirements
1. Every number on the page links to how it was measured, or is removed. Label-free proxies are named as such; unmeasured metrics are not shown.
2. Features described match what exists; planned features are clearly marked as in progress with their milestone.
3. The hero shows the product's core idea: a match turned into a point-by-point record (score + rallies + court map), using a real screenshot or recording of the new UI once M2 exists.
4. A "Research" section: court keypoints with net-band points (3D-ready), staged pipeline, honest evaluation, links to PRD/specs and repos.
5. English and Traditional Chinese, as today.
6. Page weight: initial load under 2 MB excluding the on-demand video; the video loads only when played or visible.

## Acceptance criteria
- No claim on the page lacks a source in the repos or the evaluation outputs.
- Lighthouse performance and accessibility ≥ 90 on mobile.
- Builds and deploys from `main` with one workflow.

## Out of scope
- Blog, newsletter, contact form back end.
- New visual identity for the website beyond reusing the web app's tokens (decided in the OpenSpec design).

## Dependencies
- M2 UI screenshots (rebuild-match-review-ui); M1 evaluation numbers for the court claim.
