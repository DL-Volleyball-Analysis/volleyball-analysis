#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排球動作檢測訓練腳本 - 200個epoch版本
使用 YOLOv11m 模型訓練排球動作識別，從檢查點繼續訓練
"""

from ultralytics import YOLO
import os
import yaml
import torch

def main():
    # 設定資料集路徑
    data_yaml_path = "Volleyball_Action_Dataset/data.yaml"
    
    # 自動偵測裝置
    if torch.cuda.is_available():
        device = 'cuda'
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = 'mps'
    else:
        device = 'cpu'

    # 依裝置調整預設參數
    if device == 'cuda':
        default_batch = 12
        default_workers = 8
        use_half = True
    elif device == 'mps':
        default_batch = 12
        default_workers = 4
        use_half = False
    else:  # cpu
        default_batch = 8
        default_workers = 2
        use_half = False

    print("=== 裝置偵測 ===")
    print(f"使用裝置: {device}")
    if device == 'cuda':
        try:
            props = torch.cuda.get_device_properties(0)
            total_gb = round(props.total_memory / (1024**3), 2)
            print(f"CUDA: {torch.version.cuda}, GPU 數量: {torch.cuda.device_count()}, 名稱: {props.name}, VRAM: {total_gb} GB")
        except Exception:
            print(f"CUDA: {torch.version.cuda}, GPU 數量: {torch.cuda.device_count()}, 名稱: {torch.cuda.get_device_name(0)}")
    elif device == 'mps':
        print("使用 Apple Silicon (MPS)")
    else:
        print("使用 CPU")
    print("================")
    
    # 檢查資料集配置檔案是否存在
    if not os.path.exists(data_yaml_path):
        print(f"錯誤：找不到資料集配置檔案 {data_yaml_path}")
        return
    
    # 讀取並顯示資料集資訊
    with open(data_yaml_path, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    
    print("=== 資料集資訊 ===")
    print(f"類別數量: {data_config['nc']}")
    print(f"類別名稱: {data_config['names']}")
    print(f"訓練集路徑: {data_config['train']}")
    print(f"驗證集路徑: {data_config['val']}")
    print(f"測試集路徑: {data_config['test']}")
    print("==================")
    
    # 檢查是否有現有的檢查點
    checkpoint_path = "runs/volleyball_200epoch/weights/last.pt"
    if os.path.exists(checkpoint_path):
        print(f"找到檢查點: {checkpoint_path}")
        print("將從檢查點繼續訓練...")
        model = YOLO(checkpoint_path)
    else:
        print("未找到檢查點，從預訓練模型開始...")
        model = YOLO('yolo11m.pt')
    
    # 若為 CUDA，明確指定只使用第 0 張 GPU
    device_for_ultralytics = '0' if device == 'cuda' else device

    # 設定訓練參數 - 優化版本
    training_args = {
        'data': data_yaml_path,
        'epochs': 200,
        'imgsz': 640,
        'batch': default_batch,
        'device': device_for_ultralytics,
        'project': 'runs',
        'name': 'volleyball_200epoch',
        'save': True,
        'save_period': 10,
        'cache': False,
        'workers': default_workers,
        'patience': 50,
        'lr0': 0.001,
        'lrf': 0.1,
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 3,
        'warmup_momentum': 0.8,
        'warmup_bias_lr': 0.1,
        'box': 7.5,
        'cls': 0.5,
        'dfl': 1.5,
        'val': True,
        'plots': False,
        'verbose': True,
        'amp': True,
        'half': use_half,
        'dnn': False,
    }
    
    print("開始訓練...")
    print(f"訓練參數: {training_args}")
    
    # 開始訓練
    try:
        results = model.train(**training_args)
        print("訓練完成！")
        print(f"最佳模型儲存在: runs/volleyball_200epoch/weights/best.pt")
        print(f"最後模型儲存在: runs/volleyball_200epoch/weights/last.pt")
        
        # 顯示訓練結果摘要
        print("\n=== 訓練結果摘要 ===")
        rd = getattr(results, 'results_dict', {}) or {}
        def fmt(value):
            try:
                return f"{float(value):.4f}"
            except Exception:
                return "N/A"
        print("🎯 主要指標:")
        print(f"  mAP50: {fmt(rd.get('metrics/mAP50(B)'))}")
        print(f"  mAP50-95: {fmt(rd.get('metrics/mAP50-95(B)'))}")
        print(f"  Precision: {fmt(rd.get('metrics/precision(B)'))}")
        print(f"  Recall: {fmt(rd.get('metrics/recall(B)'))}")
        print(f"  F1 Score: {fmt(rd.get('metrics/f1'))}")
        
        print("\n📊 損失函數:")
        print(f"  Box Loss: {fmt(rd.get('train/box_loss'))}")
        print(f"  Class Loss: {fmt(rd.get('train/cls_loss'))}")
        print(f"  DFL Loss: {fmt(rd.get('train/dfl_loss'))}")
        
        print("\n🔧 訓練配置:")
        print(f"  總Epochs: {training_args['epochs']}")
        print(f"  批次大小: {training_args['batch']}")
        print(f"  設備: {training_args['device']}")
        print(f"  圖像尺寸: {training_args['imgsz']}")
        
        print("\n💾 模型保存位置:")
        print(f"  最佳模型: runs/volleyball_200epoch/weights/best.pt")
        print(f"  最新模型: runs/volleyball_200epoch/weights/last.pt")
        
    except Exception as e:
        print(f"訓練過程中發生錯誤: {e}")
        return
    
    # 在測試集上評估模型
    print("\n在測試集上評估模型...")
    try:
        test_results = model.val(data=data_yaml_path, split='test', imgsz=640, device=device)
        print("測試集評估完成！")
    except Exception as e:
        print(f"測試集評估時發生錯誤: {e}")

if __name__ == "__main__":
    main()
