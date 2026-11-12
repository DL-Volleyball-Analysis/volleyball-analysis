# Review experience compared with Balltime (2026-11-12)

Balltime (now also sold as Hudl Assist) is the closest product: AI volleyball video and statistics from one camera.
Sources: Balltime Academy's guide list (`academy.balltime.com/llms.txt`), its Rally & Action Editing and FAQ pages,
and Hudl's Balltime product page. Their app was not used hands-on, so the left column is what their documentation
says, not a test.

| Review need | Balltime (documented) | This system (2026-11-12) |
|---|---|---|
| Find a moment | Rallies and Actions lists beside the player; a row plays its clip | Rally list and timeline; play-by-play list beside the video for the rally or the whole match; a row seeks the video |
| Filter | player, action, outcome, rotation, set ("Smart AI Filters") | action and player; no outcome, rotation or set yet |
| Watch a filtered set | playlists, starred clips, multi-video player | "Play these": plays the filtered actions one after another (1.5 s before to 2 s after each; overlapping clips play through) |
| Who touched the ball | each touch tagged with a player | per-player pose recognitions, **not yet matched to the ball's touches** (several players in a ready position appear together) |
| Score and rally outcome | score per rally, editable | rallies found automatically (F1 0.76 fixed, 0.742 broadcast); winners by hand |
| Ball path | ball trajectories on video, serve and attack speed, attack height | 2D ball trail on video; **3D flights** on a rotatable court with speed, apex and net-crossing height, each with its quality |
| Court | user sets court corners | found automatically (keypoints or painted lines), corrections by four clicks |
| Statistics | box score, rotation stats, attack tendencies, multi-match, AI insights | attack efficiency, kill rate, aces, serve errors per player from coach tags; CSV |
| Why a result is missing | not documented | every stage says what it found and why not (e.g. no court, camera not calibrated) |
| Correct mistakes | edit rallies, actions, players | correct court, rally winner, tags; actions are suggestions to accept or dismiss |
| Sharing, highlights, accounts | highlight builder, reels, sharing, teams | none: single user, local, no upload (by design, ADR single-user-local-deployment) |

**Where it is behind:** touch attribution (who touched the ball), outcome / rotation filters, statistics depth,
highlights and sharing. **Where it adds something:** 3D flights from one camera with stated uncertainty, automatic court
registration, transparency of every analysis stage, and data that never leaves the machine.

**Next steps that close the main gap:** touches from the ball's path and the players near it (change
smooth-rally-playback, tasks 4-5), then outcome filters and rotation once touches and winners are known.
