# PRD: smooth rally playback on amateur footage

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/smooth-rally-playback/`

## Problem
On the owner's own recording (`personal_albert_0920_1_2`, fixed phone camera beside the court, court from the owner's
CVAT label) the rendered analysis video is hard to watch and says little about the rally (owner's review, 2026-10-16):

- **The ball flickers.** The 2D map and the 3D view draw only the ball's current position, and only while a 3D flight
  covers the frame. Flights are separate pieces with gaps between them, so the ball appears and disappears; no arc is
  drawn.
- **The 2D track is broken.** VballNet finds the ball in 52% of the first 90 s, with 18 one-frame jumps over 100 px
  (lamps, ceiling) and a median run of 17 frames. WASB fine-tuned on gym footage, on the same 90 s: 68%, no jumps,
  median run 41 frames; 3D flights of ok quality grow from 15 to 20 and low-quality ones fall from 25 to 8.
- **Players flicker.** The player-only detector finds too few people on this footage, so the general detector is used;
  detection at 10 Hz loses people behind the net and in crowds, and they come back with new track ids: 126 player
  tracks in 90 s, 27 shorter than 1 s, 6 to 12 players per frame.
- **No one knows who did what.** Action labels come from a classifier trained on broadcast footage and show only for
  the frames of an event; serve, receive, set and attack are not identified per touch.

Reference: a rally visualisation shared on Threads with a smooth 2D/3D ball path (not yet viewed: the post is
restricted; the owner will record it).

## User stories
- As a player, I watch my rally with one continuous ball path on the 2D map and in 3D, and see the touch points.
- As a coach, I see each touch labelled with the player and the role in the rally: serve, receive or dig, set, attack,
  block, so I can follow "#7 receive -> #3 set -> #10 attack" without watching frame by frame.
- As a researcher, I can state how continuous the 3D rally path is and how accurate the touch roles are on labelled
  amateur rallies.

## Requirements
1. **One path per rally.** Consecutive flights meet at their touch: the end of one flight and the start of the next
   are one 3D point at one time, fitted together; gaps between flights are bridged by the fitted paths. Where a link
   is implausible (a touch the camera did not see, a jump of more than the configured distance) the path is broken
   there and says why.
2. **Drawn as a path.** The rendered video's 2D map and 3D view, and the web app's boards, draw the rally's path up
   to the current time (older part fading), touch points as markers, low-quality parts dashed. The ball marker never
   disappears inside a rally unless the path is broken.
3. **Touch roles from the rules of the game.** Each touch gets a team (side of the net at the touch), a player (the
   anchored or nearest placed player, or none) and a role from the sequence: the first touch of a rally is the serve;
   after the ball crosses the net, the receiving team's touches are numbered 1, 2, 3 (receive or dig, set, attack); a
   touch at the net right after the opponent's attack is a block and does not count. The action classifier, where it
   agrees, raises the confidence; it does not decide alone.
4. **Gym ball model.** Still cameras and gym footage use WASB (gym weights) for the ball; broadcast footage keeps
   VballNet until the broadcast test of change `train-ball-detector` decides.
5. **Stable player boxes.** Detection at a higher rate on still cameras, a longer tracker memory and re-linking of a
   lost track to a new one at the same court position, so a player keeps one box and one id through short occlusions.
6. **Measured.** Before and after on the five personal clips and the six fixed clips: ball coverage and jumps, share of
   rally time with a 3D ball position, number of path breaks per rally, player tracks per player-minute and short
   tracks; touch-role accuracy on rallies the owner labels (touch frame, player, role).

## Acceptance criteria
- Personal and fixed clips: the 3D ball path covers at least 80% of rally time (now: gaps between most flights), with
  at most two breaks per rally on median.
- Touch roles: at least 80% of labelled touches get the right role, and the right player where the player is on
  camera.
- Player tracks: short tracks (under 1 s) halved on the personal clips; at most 12 players per frame on court.
- The rendered video and the web app show no ball flicker inside a rally (checked by eye on two clips; the owner
  reviews).

## Out of scope
- Multi-camera 3D; learned 3D uplifting. Re-identification across rallies (change `add-player-reid`).
- Retraining the player detector on amateur footage (labelling loop, after this change).
- Scoring logic changes beyond using the touch sequence as a cue.

## Dependencies
- Courts for the personal clips from the owner's CVAT labels (change `add-labelling-loop`).
- Trajectory stage (constrained flights, anchors), players stage, render (`vball_app.render`), tactics board.
