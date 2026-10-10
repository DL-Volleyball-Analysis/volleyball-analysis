# Volleyball Action Recognition | 排球動作識別

YOLOv11m-based volleyball action recognition for detecting 5 action types: block, receive, serve, set, spike.

使用 YOLOv11m 模型進行排球動作識別，能夠檢測五種動作：攔網、接球、發球、舉球、扣球。

---

## Overview | 概述

This project trains a YOLOv11m model to recognize volleyball actions from video frames.

本專案使用 YOLOv11m 模型訓練排球動作識別，用於從影片幀中檢測球員動作。

## Dataset | 資料集

| Metric | Value |
|--------|-------|
| Total Images | 24,806 |
| Training | 18,616 |
| Validation | 3,636 |
| Test | 2,554 |

**Sources:**
- [Volleyball Actions Dataset](https://universe.roboflow.com/actions-players/volleyball-actions/dataset/5) (CC BY 4.0)
- [Volleyball Action Recognition Dataset](https://universe.roboflow.com/vbanalyzer/volleyball-action-recognition-k6tqv/dataset/6)

**Download (Recommended):** [Google Drive](https://drive.google.com/drive/folders/1lvWUwkBAEeCGJoM7Z5gwE71ngi94xQB5?usp=share_link)

## Action Classes | 動作類別

| ID | English | 中文 | Description |
|----|---------|------|-------------|
| 0 | block | 攔網 | Player blocking at the net |
| 1 | receive | 接球 | Receiving serve or spike |
| 2 | serve | 發球 | Serving the ball |
| 3 | set | 舉球 | Setting for teammate |
| 4 | spike | 扣球 | Attacking/spiking |

## Model Specifications | 模型規格

- **Architecture:** YOLOv11m (Medium)
- **Parameters:** 20,056,863
- **Layers:** 231
- **GFLOPs:** 68.2

## Results | 結果

From the training log of the final model (epoch 190), **validation** split: precision 0.916, recall 0.915,
mAP@0.5 0.945, mAP@0.5:0.95 0.755. Test split (measured 2026-10-10 with `scripts/eval_actions.py`): mAP@0.5 0.957, mAP@0.5:0.95 0.790; test frames come from the same matches as training, so this is not an unseen-match score ([docs/results/actions.md](../../docs/results/actions.md)). See
[docs/results/action-recognition.md](../../docs/results/action-recognition.md).

## Training Configuration | 訓練配置

| Parameter | Value |
|-----------|-------|
| Framework | Ultralytics YOLO |
| Epochs | 200 |
| Batch Size | 12 (final run on a CUDA GPU, `args.yaml`) |
| Image Size | 640x640 |
| Optimizer | `auto` (Ultralytics chooses optimizer and learning rate; the `lr0=0.001` setting is then ignored) |
| Early stopping | patience 50 (stopped at epoch 190) |
| Device | MPS / CUDA / CPU |

## Quick Start | 快速開始

```bash
# Clone and setup
git clone https://github.com/DL-Volleyball-Analysis/volleyball-analysis.git
cd volleyball-analysis/training/action-recognition
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Train
python train_volleyball.py
```

## Inference | 推理

```python
from ultralytics import YOLO

model = YOLO('runs/volleyball_200epoch/weights/best.pt')
results = model('path/to/image.jpg')
results[0].show()
```

## Project Structure | 專案結構

```
training/action-recognition/
├── README.md
├── train_volleyball.py      # Training script (downloads the yolo11m.pt base model on first run)
├── requirements.txt
└── Volleyball_Action_Dataset/  # Dataset (not in repo)
```

## License | 授權

Dataset: CC BY 4.0

---

*Part of [DL-Volleyball-Analysis](https://github.com/DL-Volleyball-Analysis) - Senior Capstone Project*