# Action recognition (capstone): results

From the capstone's training logs (`runs/volleyball_200epoch*/results.csv` and `args.yaml`, kept on the
team's Drive; the training code is in
[action-recognition-yolov11](https://github.com/DL-Volleyball-Analysis/action-recognition-yolov11)).
Five classes: receive, set, block, spike, serve. Merged Roboflow volleyball action datasets
(24,806 images: 18,616 train, 3,636 validation, 2,554 test, per the capstone report).

| Model | Input | Epochs run | mAP@0.5 (last / best) | mAP@0.5:0.95 (last) |
|---|---|---|---|---|
| YOLOv11m | 640 | 190 (early stop, patience 50) | 0.9449 / 0.9472 (epoch 137) | 0.755 |
| YOLOv11n | 640 | 200 | 0.9373 / 0.9373 | 0.694 |

**These are validation-split numbers** (ultralytics logs validation metrics during training); no test-split
evaluation was found. The Roboflow sources are frame collections, so near-duplicate frames may sit in
both splits; the numbers may overstate accuracy on unseen matches.

Numbers in the capstone report without a record (scene-wise ball accuracy, player-tracking consistency,
jersey OCR rate, YOLOv8 and TrackNet comparisons) are not reproduced here.
