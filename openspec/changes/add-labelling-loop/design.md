# Design

## Decisions

**Prefill and correct.** Every task starts from the pipeline's output on that frame; the user's action (accept, move,
add, delete) is what is stored, plus the final value. Accepted predictions count as labels only when explicitly
accepted, never by default, so unseen errors do not enter the data.

**Partial labels.** A label record is (video, frame, task, value, author, time, version). A frame labelled for court
only is still a valid sample; training masks the other tasks.

**Split by video.** Frames of one video are strongly correlated; the dataset assigns whole videos to train, val or
test, and the test videos are chosen once and kept fixed so results stay comparable across retrainings.

**Hardest frames first.** The queue orders frames by the pipeline's own doubt (court status not ok, ball missed
between detections, more than twelve player boxes, low action confidence), so labelling time goes where it helps most.

**Storage.** Labels live in the app database (backed up by vball_app.backup) and export to files under
data/datasets/own_labels/, git-ignored like other data.

## Risks
Correcting biases labels towards the model's output (anchoring). The UI shows the prediction faintly and requires a
deliberate accept; a sample of frames is labelled from scratch to measure the bias.
