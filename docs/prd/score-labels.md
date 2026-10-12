# Rally and point labels from the on-screen score

Version 1.0 · 2026-10-12 · Owner: YuJia Liang · Parent: [rally-detection.md](rally-detection.md)

## Why
The rally model was trained on broadcast matches, where the time between rallies shows close-ups and replays, so it
learned "court in view and both teams visible = play". A fixed end-line camera always shows the court and both teams:
that cue is useless there, and on all six fixed clips the stage reports the footage as out of training. Training a
fixed-camera rally model needs labelled fixed-camera matches, and automatic scoring needs labelled point winners;
neither exists.

The fixed-camera matches we use (VolleyballWatchdog, NCAA men's volleyball) carry a score bug at the top of the frame,
e.g. "Z4 (1) 06-04 (0) Z5": sets won and points per team. Tesseract reads it (checked on four frames: every score
right). A point change marks the end of a rally and says which team won it.

## What
1. Score reading: the score bug read once per second (Tesseract), cleaned (a score only moves forward by one point,
   or resets at a new set), giving the times of point changes and the team that scored.
2. Labels per match: rally ends (a few seconds before each change; the delay measured on hand-checked changes) and
   point winners, saved next to the video.
3. Use: (a) evaluate rally detection and point-winner calls on fixed cameras; (b) train a fixed-camera rally model on
   cues from the pipeline's own results (court, players, ball), split by match.
4. Data: eight full matches from different arenas (720p, local only, research use), separate from the matches of the
   six test clips.

## Success
- Score reading: every point change on two hand-checked matches found, no false changes.
- A fixed-camera rally model measured on held-out matches (rally count, end-time error) and reported honestly.

## Out of scope
Score bugs of other broadcasters (each needs its crop and pattern); rally start times (serves) beyond what the cues give.
