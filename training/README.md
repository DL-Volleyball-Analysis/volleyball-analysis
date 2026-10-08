# Training

Training code for the capstone's player models. GPU training runs on Google Colab or a CUDA machine;
datasets, `runs/` outputs and weights stay out of git (finished weights go in the root `models/`).

| Folder | Model | Result (validation split) |
|---|---|---|
| [action-recognition](action-recognition) | YOLOv11m, five actions (serve, receive, set, spike, block) | mAP@0.5 0.945, mAP@0.5:0.95 0.755 |
| [jersey-numbers](jersey-numbers) | YOLOv8m jersey number detector | mAP@0.5 0.966, mAP@0.5:0.95 0.734 ([log](jersey-numbers/results/results.csv)) |

The court keypoint model is trained from [`notebooks/train_court_keypoints.ipynb`](../notebooks/train_court_keypoints.ipynb).

Moved here from the archived repositories
[action-recognition-yolov11](https://github.com/DL-Volleyball-Analysis/action-recognition-yolov11) and
[jersey-number-detection](https://github.com/DL-Volleyball-Analysis/jersey-number-detection), which keep
the full history and training plots; the `yolo11m.pt` base model is downloaded by Ultralytics.
