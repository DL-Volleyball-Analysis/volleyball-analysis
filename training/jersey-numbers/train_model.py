"""
訓練球衣號碼檢測模型
使用 YOLOv8 訓練模型
"""

import os
import torch
from pathlib import Path
from ultralytics import YOLO
import yaml

# 配置
DATASET_DIR = Path("datasets/processed/merged")
DATA_YAML = DATASET_DIR / "data.yaml"
RUNS_DIR = Path("runs/jersey_detection")
MODEL_NAME = "yolov8m.pt"  # 使用 Medium 模型以獲得更好的準確度，可選: yolov8n.pt, yolov8s.pt, yolov8m.pt, yolov8l.pt, yolov8x.pt


def validate_dataset():
    """驗證資料集結構"""
    print("正在驗證資料集...")
    
    if not DATA_YAML.exists():
        print(f"✗ 錯誤: 找不到配置文件 {DATA_YAML}")
        print("請先運行 organize_datasets.py 來組織資料集")
        return False
    
    # 讀取配置
    with open(DATA_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    train_dir = DATASET_DIR / data['train'].replace('images', '')
    val_dir = DATASET_DIR / data['val'].replace('images', '')
    
    # 檢查目錄是否存在
    if not train_dir.exists():
        print(f"✗ 錯誤: 找不到訓練集目錄 {train_dir}")
        return False
    
    if not val_dir.exists():
        print(f"✗ 錯誤: 找不到驗證集目錄 {val_dir}")
        return False
    
    # 檢查圖片和標籤數量
    train_images = len(list((train_dir / "images").glob("*")))
    train_labels = len(list((train_dir / "labels").glob("*.txt")))
    val_images = len(list((val_dir / "images").glob("*")))
    val_labels = len(list((val_dir / "labels").glob("*.txt")))
    
    print(f"✓ 訓練集: {train_images} 張圖片, {train_labels} 個標籤")
    print(f"✓ 驗證集: {val_images} 張圖片, {val_labels} 個標籤")
    print(f"✓ 類別數量: {data['nc']}")
    
    if train_images == 0 or val_images == 0:
        print("✗ 錯誤: 資料集為空")
        return False
    
    return True


def check_cuda():
    """檢查 CUDA 可用性並返回 GPU 資訊"""
    print("\n檢查 CUDA 環境...")
    
    if torch.cuda.is_available():
        print(f"✓ CUDA 可用")
        print(f"  CUDA 版本: {torch.version.cuda}")
        print(f"  PyTorch 版本: {torch.__version__}")
        print(f"  GPU 數量: {torch.cuda.device_count()}")
        
        gpu_info = {}
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            name = props.name
            total_memory_gb = props.total_memory / 1024**3
            
            print(f"  GPU {i}: {name}")
            print(f"    記憶體: {total_memory_gb:.2f} GB")
            
            # 保存第一個 GPU 的資訊
            if i == 0:
                gpu_info = {
                    'name': name,
                    'total_memory_gb': total_memory_gb,
                    'total_memory_bytes': props.total_memory,
                    'major': props.major,
                    'minor': props.minor
                }
        
        return True, gpu_info
    else:
        print("⚠️  CUDA 不可用，將使用 CPU 訓練（速度較慢）")
        return False, None


def optimize_batch_size(gpu_info, model_name):
    """根據 GPU 記憶體和模型大小優化 batch size"""
    if not gpu_info:
        return 8
    
    total_memory_gb = gpu_info['total_memory_gb']
    
    # 根據模型大小和 GPU 記憶體決定 batch size
    # RTX 5060 (8GB) 的推薦配置
    model_batch_configs = {
        'yolov8n.pt': {'small': 64, 'medium': 48, 'large': 32},   # Nano
        'yolov8s.pt': {'small': 48, 'medium': 32, 'large': 24},   # Small
        # 注意：對於 12GB VRAM，YOLOv8m 的 'small' 配置設為 16 以避免 OOM
        # 對於 8GB VRAM (RTX 5060)，會使用 'small' 配置，batch size 為 16
        'yolov8m.pt': {'small': 16, 'medium': 24, 'large': 16},   # Medium (優化以避免 OOM)
        'yolov8l.pt': {'small': 24, 'medium': 16, 'large': 12},  # Large
        'yolov8x.pt': {'small': 16, 'medium': 12, 'large': 8},   # XLarge
    }
    
    # 根據 GPU 記憶體選擇配置
    if total_memory_gb >= 8:
        config_key = 'small'
    elif total_memory_gb >= 6:
        config_key = 'medium'
    else:
        config_key = 'large'
    
    batch_size = model_batch_configs.get(model_name, model_batch_configs['yolov8n.pt'])[config_key]
    
    print(f"  → 優化 Batch Size: {batch_size} (基於 {model_name} 和 {total_memory_gb:.1f}GB GPU)")
    return batch_size


def optimize_image_size(gpu_info, model_name):
    """根據 GPU 記憶體和模型大小優化圖片大小"""
    if not gpu_info:
        return 640
    
    total_memory_gb = gpu_info['total_memory_gb']
    
    # 較小的模型可以使用更大的圖片尺寸
    if 'yolov8n.pt' in model_name or 'yolov8s.pt' in model_name:
        # 小型模型：如果 GPU 記憶體足夠，使用更大的圖片尺寸
        img_size = 832 if total_memory_gb >= 8 else 640
    else:
        # 較大模型：使用標準尺寸
        img_size = 640
    
    print(f"  → 優化 Image Size: {img_size}x{img_size}")
    return img_size


def optimize_workers(gpu_info):
    """根據系統資源優化 workers 數量"""
    if not gpu_info:
        return 4
    
    import os
    # 獲取 CPU 核心數
    cpu_count = os.cpu_count() or 4
    
    # Windows 推薦使用較少的 workers (如 4) 以避免多工錯誤
    # 原本 min(12, ...) 在 Windows 上太高，會導致 'shared file mapping' 錯誤
    # 保留一些核心給系統，並確保至少有 1 個 worker
    workers = min(4, max(1, cpu_count - 2))
    
    print(f"  → 優化 Workers: {workers} (CPU 核心數: {cpu_count})")
    return workers


def train():
    """訓練模型"""
    print("=" * 60)
    print("開始訓練球衣號碼檢測模型")
    print("=" * 60)
    
    # 檢查 CUDA
    use_cuda, gpu_info = check_cuda()
    
    # 驗證資料集
    if not validate_dataset():
        return
    
    # 檢查模型文件
    model_path = MODEL_NAME
    print(f"\n使用模型: {model_path}")
    
    # 載入模型
    try:
        model = YOLO(model_path)
        print(f"✓ 成功載入模型")
    except Exception as e:
        print(f"✗ 載入模型失敗: {e}")
        print("模型將自動下載...")
        model = YOLO(model_path)
    
    # 決定使用哪個設備和優化參數
    if use_cuda:
        device = 0  # 使用第一個 GPU
        workers = optimize_workers(gpu_info)
        batch_size = optimize_batch_size(gpu_info, MODEL_NAME)
        img_size = optimize_image_size(gpu_info, MODEL_NAME)
    else:
        device = 'cpu'
        workers = 4
        batch_size = 8
        img_size = 640
    
    # 訓練參數
    print("\n訓練配置:")
    print(f"  資料集: {DATA_YAML}")
    print(f"  輸出目錄: {RUNS_DIR}")
    print(f"  模型: {model_path}")
    print(f"  設備: {'GPU (CUDA)' if use_cuda else 'CPU'}")
    if use_cuda and gpu_info:
        print(f"  GPU: {gpu_info['name']} ({gpu_info['total_memory_gb']:.2f} GB)")
    print(f"  Batch Size: {batch_size}")
    print(f"  Image Size: {img_size}")
    print(f"  Workers: {workers}")
    
    # 開始訓練
    print("\n開始訓練...")
    print("=" * 60)
    
    try:
        
        results = model.train(
            data=str(DATA_YAML),
            epochs=100,
            imgsz=img_size,
            batch=batch_size,
            name="jersey_detection",
            project=str(RUNS_DIR.parent),
            exist_ok=True,
            patience=20,  # 早停耐心值
            save=True,
            save_period=10,  # 每10個epoch保存一次
            val=True,
            plots=True,
            device=device,
            workers=workers,
            optimizer='AdamW',
            lr0=0.001,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,
            warmup_bias_lr=0.1,
            box=7.5,
            cls=0.5,
            dfl=1.5,
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=0.0,
            translate=0.1,
            scale=0.5,
            shear=0.0,
            perspective=0.0,
            flipud=0.0,
            fliplr=0.5,
            mosaic=1.0,
            mixup=0.0,
            copy_paste=0.0,
            amp=True,  # 啟用混合精度訓練（自動混合精度），可提高速度並節省記憶體
            cache=False,  # 如果記憶體足夠，可以設為 True 或 'ram' 來加速
            close_mosaic=10,  # 最後10個epoch關閉mosaic增強以提高精度
        )
        
        print("\n" + "=" * 60)
        print("訓練完成!")
        print("=" * 60)
        print(f"\n最佳模型位置: {results.save_dir / 'weights' / 'best.pt'}")
        print(f"最新模型位置: {results.save_dir / 'weights' / 'last.pt'}")
        print(f"\n結果目錄: {results.save_dir}")
        
    except Exception as e:
        print(f"\n✗ 訓練過程出錯: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 設置 CUDA 設備（如果有多個 GPU，可以指定使用哪一個）
    # 例如：使用第一個 GPU -> '0'，使用第二個 GPU -> '1'
    # 如果不設置，將使用所有可用的 GPU
    # os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    
    # 優化 CUDA 設置以充分利用 GPU
    if torch.cuda.is_available():
        # 啟用 cuDNN 自動調優
        torch.backends.cudnn.benchmark = True
        # 啟用 TensorFloat-32 (TF32) 以加速訓練（Ampere 及以上架構）
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print("✓ 已啟用 CUDA 優化設置")
    
    train()

