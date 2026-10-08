"""
組織和合併多個資料集腳本
將下載的資料集合併成統一的 YOLOv8 格式
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import yaml

# 目錄配置
RAW_DATASETS_DIR = Path("datasets/raw")
PROCESSED_DATASETS_DIR = Path("datasets/processed")
MERGED_DATASET_DIR = PROCESSED_DATASETS_DIR / "merged"
TRAIN_DIR = MERGED_DATASET_DIR / "train"
VAL_DIR = MERGED_DATASET_DIR / "val"
TEST_DIR = MERGED_DATASET_DIR / "test"


def get_all_classes_from_datasets():
    """從所有資料集中收集所有類別"""
    all_class_ids = set()
    
    for dataset_dir in RAW_DATASETS_DIR.iterdir():
        if not dataset_dir.is_dir():
            continue
            
        # 尋找 data.yaml 文件
        data_yaml = dataset_dir / "data.yaml"
        if data_yaml.exists():
            try:
                with open(data_yaml, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if 'names' in data:
                        if isinstance(data['names'], dict):
                            # 如果是字典，獲取所有類別ID
                            all_class_ids.update([int(k) for k in data['names'].keys()])
                        elif isinstance(data['names'], list):
                            # 如果是列表，類別ID就是索引
                            all_class_ids.update(range(len(data['names'])))
            except Exception as e:
                print(f"  警告: 無法讀取 {data_yaml}: {e}")
        
        # 也檢查 train/valid/test 目錄中的標籤文件
        for split in ['train', 'valid', 'test', 'val']:
            labels_dir = dataset_dir / split / "labels"
            if labels_dir.exists():
                for label_file in labels_dir.glob("*.txt"):
                    try:
                        with open(label_file, 'r') as f:
                            for line in f:
                                parts = line.strip().split()
                                if parts:
                                    class_id = int(parts[0])
                                    all_class_ids.add(class_id)
                    except Exception as e:
                        continue
    
    # 排序並返回類別ID列表
    sorted_class_ids = sorted(list(all_class_ids))
    
    # 如果沒有找到類別，使用預設的 0-99
    if not sorted_class_ids:
        sorted_class_ids = list(range(100))
    
    return sorted_class_ids


def create_class_mapping(all_class_ids):
    """創建統一的類別映射"""
    # 排序並創建映射：原始類別ID -> 新類別ID（從0開始）
    sorted_classes = sorted(all_class_ids)
    
    if not sorted_classes:
        sorted_classes = list(range(100))
    
    class_mapping = {}
    for new_id, old_id in enumerate(sorted_classes):
        class_mapping[old_id] = new_id
    
    return class_mapping, sorted_classes


def copy_and_convert_dataset(dataset_dir, output_train_dir, output_val_dir, output_test_dir, 
                             class_mapping, split_ratio=(0.7, 0.2, 0.1)):
    """複製並轉換資料集，重新映射類別ID"""
    stats = defaultdict(int)
    
    # 尋找 train/valid/test 目錄
    splits = {}
    for split_name in ['train', 'valid', 'val', 'test']:
        split_dir = dataset_dir / split_name
        if split_dir.exists():
            splits[split_name] = split_dir
    
    if not splits:
        print(f"  警告: {dataset_dir.name} 中未找到 train/valid/test 目錄")
        return stats
    
    # 處理每個分割
    for split_name, split_dir in splits.items():
        images_dir = split_dir / "images"
        labels_dir = split_dir / "labels"
        
        if not images_dir.exists() or not labels_dir.exists():
            continue
        
        # 決定輸出目錄
        if split_name == 'train':
            out_images_dir = output_train_dir / "images"
            out_labels_dir = output_train_dir / "labels"
        elif split_name == 'valid' or split_name == 'val':
            out_images_dir = output_val_dir / "images"
            out_labels_dir = output_val_dir / "labels"
        elif split_name == 'test':
            out_images_dir = output_test_dir / "images"
            out_labels_dir = output_test_dir / "labels"
        else:
            continue
        
        out_images_dir.mkdir(parents=True, exist_ok=True)
        out_labels_dir.mkdir(parents=True, exist_ok=True)
        
        # 處理所有圖片和標籤
        image_files = list(images_dir.glob("*"))
        for img_file in image_files:
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                continue
            
            # 複製圖片
            dest_img = out_images_dir / f"{dataset_dir.name}_{img_file.name}"
            shutil.copy2(img_file, dest_img)
            stats[f"{split_name}_images"] += 1
            
            # 處理對應的標籤文件
            label_file = labels_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                dest_label = out_labels_dir / f"{dataset_dir.name}_{img_file.stem}.txt"
                
                # 讀取並轉換類別ID
                with open(label_file, 'r') as f_in, open(dest_label, 'w') as f_out:
                    for line in f_in:
                        parts = line.strip().split()
                        if parts:
                            old_class_id = int(parts[0])
                            # 如果類別在映射中，使用新ID；否則跳過
                            if old_class_id in class_mapping:
                                new_class_id = class_mapping[old_class_id]
                                parts[0] = str(new_class_id)
                                f_out.write(' '.join(parts) + '\n')
                                stats[f"{split_name}_labels"] += 1
    
    return stats


def create_data_yaml(output_dir, class_names):
    """創建 data.yaml 配置文件"""
    data_config = {
        'path': str(output_dir.absolute()),
        'train': 'train/images',
        'val': 'val/images',
        'test': 'test/images',
        'nc': len(class_names),
        'names': class_names
    }
    
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"\n✓ 創建配置文件: {yaml_path}")
    return yaml_path


def main():
    """主函數"""
    print("=" * 60)
    print("資料集組織和合併工具")
    print("=" * 60)
    
    if not RAW_DATASETS_DIR.exists():
        print(f"\n✗ 錯誤: 找不到原始資料集目錄: {RAW_DATASETS_DIR}")
        print("請先運行 download_datasets.py 下載資料集")
        return
    
    # 創建輸出目錄
    TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    VAL_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    (TRAIN_DIR / "images").mkdir(parents=True, exist_ok=True)
    (TRAIN_DIR / "labels").mkdir(parents=True, exist_ok=True)
    (VAL_DIR / "images").mkdir(parents=True, exist_ok=True)
    (VAL_DIR / "labels").mkdir(parents=True, exist_ok=True)
    (TEST_DIR / "images").mkdir(parents=True, exist_ok=True)
    (TEST_DIR / "labels").mkdir(parents=True, exist_ok=True)
    
    # 獲取所有類別
    print("\n正在分析資料集類別...")
    all_class_ids = get_all_classes_from_datasets()
    class_mapping, sorted_classes = create_class_mapping(all_class_ids)
    
    # 創建類別名稱列表 (0-99 的球衣號碼)
    class_names = [str(i) for i in sorted_classes]
    
    print(f"\n找到 {len(class_names)} 個類別:")
    print(f"  類別範圍: {min(sorted_classes)} - {max(sorted_classes)}")
    
    # 合併所有資料集
    print("\n正在合併資料集...")
    all_stats = defaultdict(int)
    
    dataset_dirs = [d for d in RAW_DATASETS_DIR.iterdir() if d.is_dir()]
    if not dataset_dirs:
        print(f"\n✗ 錯誤: 在 {RAW_DATASETS_DIR} 中未找到任何資料集")
        return
    
    for dataset_dir in dataset_dirs:
        print(f"\n處理: {dataset_dir.name}")
        stats = copy_and_convert_dataset(
            dataset_dir, TRAIN_DIR, VAL_DIR, TEST_DIR, class_mapping
        )
        for key, value in stats.items():
            all_stats[key] += value
    
    # 創建 data.yaml
    yaml_path = create_data_yaml(MERGED_DATASET_DIR, class_names)
    
    # 顯示統計信息
    print("\n" + "=" * 60)
    print("合併完成統計:")
    print("=" * 60)
    print(f"訓練集圖片: {all_stats.get('train_images', 0)}")
    print(f"訓練集標籤: {all_stats.get('train_labels', 0)}")
    print(f"驗證集圖片: {all_stats.get('valid_images', 0) + all_stats.get('val_images', 0)}")
    print(f"驗證集標籤: {all_stats.get('valid_labels', 0) + all_stats.get('val_labels', 0)}")
    print(f"測試集圖片: {all_stats.get('test_images', 0)}")
    print(f"測試集標籤: {all_stats.get('test_labels', 0)}")
    print(f"\n合併後的資料集位置: {MERGED_DATASET_DIR}")
    print(f"配置文件: {yaml_path}")
    print("\n下一步: 運行 train_model.py 開始訓練模型")


if __name__ == "__main__":
    main()

