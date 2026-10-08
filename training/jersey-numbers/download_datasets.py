"""
下載 Roboflow 資料集腳本
用於下載多個球衣號碼檢測資料集並組織到統一結構中
"""

import os
import shutil
from pathlib import Path
from roboflow import Roboflow

# 資料集配置
DATASETS = [
    {
        "name": "volleyai-actions-jersey-number-detection",
        "workspace": "volleyai-actions",
        "project": "jersey-number-detection-s01j4",
        "version": 1
    },
    {
        "name": "workspace67-jersey",
        "workspace": "workspace67",
        "project": "jersey-fxmll",
        "version": 1
    },
    {
        "name": "teste-player-number-detect",
        "workspace": "teste-5efoz",
        "project": "player-number-detect",
        "version": 1
    },
    {
        "name": "hgjhj-jersey-number-detection",
        "workspace": "hgjhj",
        "project": "jersey-number-detection-br3ld",
        "version": 1
    }
]

# 輸出目錄
DATASETS_DIR = Path("datasets")
RAW_DATASETS_DIR = DATASETS_DIR / "raw"
PROCESSED_DATASETS_DIR = DATASETS_DIR / "processed"


def download_dataset(rf, dataset_info):
    """下載單個資料集"""
    print(f"\n正在下載資料集: {dataset_info['name']}")
    print(f"  Workspace: {dataset_info['workspace']}")
    print(f"  Project: {dataset_info['project']}")
    
    try:
        project = rf.workspace(dataset_info['workspace']).project(dataset_info['project'])
        dataset = project.version(dataset_info['version']).download(
            model_format="yolov8",
            location=str(RAW_DATASETS_DIR / dataset_info['name'])
        )
        print(f"  ✓ 成功下載到: {RAW_DATASETS_DIR / dataset_info['name']}")
        return True
    except Exception as e:
        print(f"  ✗ 下載失敗: {str(e)}")
        return False


def main():
    """主函數"""
    print("=" * 60)
    print("球衣號碼檢測資料集下載工具")
    print("=" * 60)
    
    # 創建目錄
    RAW_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 檢查是否設置了 Roboflow API Key
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        print("\n⚠️  警告: 未找到 ROBOFLOW_API_KEY 環境變數")
        print("請先設置您的 Roboflow API Key:")
        print("  export ROBOFLOW_API_KEY='your_api_key_here'")
        print("\n或在使用此腳本前運行:")
        print("  export ROBOFLOW_API_KEY=$(roboflow login)")
        return
    
    # 初始化 Roboflow
    try:
        rf = Roboflow(api_key=api_key)
        print(f"\n✓ Roboflow API 連接成功")
    except Exception as e:
        print(f"\n✗ Roboflow API 連接失敗: {str(e)}")
        return
    
    # 下載所有資料集
    success_count = 0
    for dataset_info in DATASETS:
        if download_dataset(rf, dataset_info):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"下載完成: {success_count}/{len(DATASETS)} 個資料集成功下載")
    print("=" * 60)
    print(f"\n原始資料集位置: {RAW_DATASETS_DIR}")
    print(f"處理後的資料集位置: {PROCESSED_DATASETS_DIR}")
    print("\n下一步: 運行 organize_datasets.py 來合併和組織資料集")


if __name__ == "__main__":
    main()

