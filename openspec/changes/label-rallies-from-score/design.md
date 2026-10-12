# Design

## Reading
Crop: the score bug band (top 40 px at 720p, the centre third of the width; per channel constant in SCOREBUGS). Grey,
2x upscale, Otsu threshold, Tesseract `--psm 7` with a digit/parenthesis whitelist. Pattern `\((\d)\)\s*(\d{1,2})-(\d{1,2})\s*\((\d)\)`
-> (sets_a, points_a, points_b, sets_b). Unreadable frames (replays, graphics) are skipped.

## Cleaning
Read once per second. A score is accepted when it is read the same in 2 consecutive readings. Accepted scores must
move forward: one team +1 point, or a set change (the set count of one team +1, points back to 0-0). Anything else
is a misread and is dropped. A point change at time t: team a or b scored, rally ended before t.

## Labels
`labels/<video id>.json`: {"changes": [{"t", "team", "score": [sa, pa, pb, sb]}], "read_share"}. The delay between the
end of a rally and the bug update is measured on a hand-checked sample and stored with the labels, not guessed.

## Data split
Eight matches, different arenas, none of them the matches of the six test clips; train / test split by match.
