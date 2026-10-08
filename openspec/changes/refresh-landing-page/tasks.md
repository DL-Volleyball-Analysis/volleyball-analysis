# Tasks

## 1. Housekeeping (branch `cleanup`)

- [x] 1.1 Remove unreferenced components and unused packages and verify `npm run build` passes (done 2026-10-08: 40 files, 30 packages)
- [x] 1.2 Keep only `deploy.yml` and verify a single Pages workflow remains in `.github/workflows/`
- [x] 1.3 Switch the hero video to `demo.mp4` after verifying it matches `demo.mov` frame by frame (mean abs diff ≤ 0.4/255)

## 2. Truthful claims

- [ ] 2.1 Add `lib/claims.ts` with required sources and render `Stats` from it; verify the build fails type-checking if an entry has no source
- [ ] 2.2 Fill the initial entries from `outputs/ball_model_comparison/metrics.csv` and the upstream benchmark; verify each value against its source file
- [ ] 2.3 Remove the unsourced stats and the "automatic court detection" claim from both languages; verify `grep` finds no "98.5" or "100K" in the repo

## 3. Copy and sections

- [ ] 3.1 Add feature status and milestone; rewrite feature and how-it-works copy (EN + ZH) for the current pipeline; verify every available feature exists in the web app
- [ ] 3.2 Add the Research section with links to PRD, specs and repos; verify all links resolve
- [ ] 3.3 Verify every section renders in both languages with no missing translation keys (type check on `translations.ts`)

## 4. Performance

- [ ] 4.1 Lazy-load the hero video with a poster frame and verify in the network panel that the video is not requested before it is near the viewport
- [ ] 4.2 Verify initial load < 2 MB and Lighthouse mobile performance and accessibility ≥ 90; record the numbers in the repo README

## 5. After M2

- [ ] 5.1 Replace the hero capture with a recording of the new match page and verify the poster and video show the new UI

## Workflow follow-up

- Push `cleanup` and the content branch and open pull requests in the org only after the owner's OK.
- Archive the change after deploy.
