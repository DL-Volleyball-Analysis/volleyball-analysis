# Tasks

## 1. CVAT
- [ ] 1.1 Self-hosted CVAT with Docker; docs/labelling.md (setup, the owner creates the admin account, project labels)
- [ ] 1.2 Project with labels: player (track, id), court (14-point skeleton), ball (point), action attribute, source attribute

## 2. Converters
- [ ] 2.1 `vball.datasets.cvat` export of pipeline output as pre-annotations; frames ordered by the pipeline's doubt
- [ ] 2.2 Import of CVAT exports into the dataset format, human-touched items only, split by video; tests
- [ ] 2.3 Round trip on SportsMOT ground truth scores 1.0; overlay sheets; label sanity checks
- [x] 2.4 Court labels straightened: sideline points and each net post (net bottom, top, centre point) moved perpendicular onto their fitted line (`cvat.straighten`); position along the line kept

## 3. First labels
- [ ] 3.1 Court points of the five amateur clips; court error on them in docs/results
- [ ] 3.2 Re-labelled subset for the labeller's consistency
