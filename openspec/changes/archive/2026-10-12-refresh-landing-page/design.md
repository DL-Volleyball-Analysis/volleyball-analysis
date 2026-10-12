# Design

## Context

Next.js 14 static export on GitHub Pages (`output: 'export'`, base path `/volleyvision-website`). Copy lives in `lib/translations.ts` (EN + ZH) behind `LanguageContext`. The housekeeping part is on local branch `cleanup` (see proposal).

## Goals / Non-Goals

**Goals:** truthful copy driven from one place; the stats strip fed by a small data file with sources, so updating a number is a one-line change.
**Non-Goals:** migrating off Next.js (static export works and the site is separate from the web app); a redesign of the visual identity.

## Decisions

### Claims as data
Add `lib/claims.ts`: `{ value, label: {en, zh}, kind: 'labelled' | 'proxy' | 'benchmark', source: url }[]`. `Stats` renders only entries with a source; the type makes `source` required. Initial entries: ball-model jump reduction and detection rate on 5 broadcast clips (proxy, from `scripts/compare_ball_models.py` output), upstream VballNet V4c F1 0.902 (benchmark, upstream README). Court error is added after M1's evaluation.
*Alternative:* hard-code in the component (today) — rejected, it is how unsourced numbers got in.

### Feature status as data
Feature cards get `status: 'available' | 'in-progress'` and `milestone`. In-progress cards render a "In progress · M3" badge. Copy comes from `translations.ts` as now.

### Lazy video
`HeroVideo` uses `preload="none"` and starts loading via `IntersectionObserver` when within one viewport of view; a poster frame (JPEG, < 200 KB) is shown before.

### Keep Next.js here
The site is static and already works; rewriting it in Vite gains nothing for visitors. Shared tokens with the web app are optional and not part of this change.

### Visual reference (owner, 2026-10-08)
`~/Documents/Soredemo/soredemo-web`, applied as in `rebuild-match-review-ui` design "revision 2": the
hero shows the match-review editor as a working illustration (captioned as such until real footage
exists), system fonts, documented contrast, mono only for machine-origin strings. Soredemo's brand
elements (menu bar, notch, desk objects, Apple artwork) are not reused.

## Risks / Trade-offs

- [Fewer impressive numbers] → Intended; credibility matters more for reviewers. The research section carries the substance.
- [Screenshots depend on M2] → Ship the truthful copy first; swap the hero capture when M2 lands (separate task group).
