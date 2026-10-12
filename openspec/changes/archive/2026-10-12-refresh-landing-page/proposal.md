# Proposal

## Why

The public landing page still presents the capstone system and states unmeasured numbers ("98.5% detection accuracy", "100K+ frames analyzed") and a feature that did not exist ("automatic court detection"). It is the first thing grad-school reviewers see. Implements [docs/prd/landing-page.md](../../../docs/prd/landing-page.md); repository clean-up context in [docs/repo-organization.md](../../../docs/repo-organization.md).

## What Changes

- Housekeeping (already done locally on branch `cleanup`, no visible change): remove 40 unreferenced components and 30 unused packages, keep one deploy workflow, serve the identical 4 MB `demo.mp4` instead of the 66 MB `demo.mov`.
- Replace the stats strip with measured numbers only, each linked to its source; drop the rest.
- Rewrite features and "how it works" to describe the current pipeline (ball tracking, learned court keypoints, staged analysis, rally review) and mark planned parts with their milestone.
- New hero centred on the point-by-point match record; uses a real capture of the new match page once M2 exists, the current demo video until then.
- Add a Research section linking PRD, OpenSpec specs and repositories.
- Lazy-load the demo video.

Out of scope: blog, contact back end, a new brand identity.

## Capabilities

### New Capabilities
- `landing-page`: what the public site states and shows about the system, and the evidence rules for its claims.

### Modified Capabilities

## Impact

- Repo `volleyvision-website`: `components/` (Stats, Features, HowItWorks, Hero/HeroVideo, new Research), `lib/translations.ts` (EN + ZH copy), `.github/workflows/`, `package.json`.
- No impact on `vball` or the web app.
