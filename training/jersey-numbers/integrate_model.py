"""
整合球衣號碼檢測模型到排球分析專案
將訓練好的模型複製到專案並更新相關代碼
"""

import os
import shutil
from pathlib import Path

# 配置
CURRENT_DIR = Path(__file__).parent
PROJECT_DIR = CURRENT_DIR.parents[1]  # repository root (this folder is training/jersey-numbers)
MODEL_SOURCE = CURRENT_DIR / "runs" / "jersey_detection" / "weights" / "best.pt"
MODEL_DEST = PROJECT_DIR / "models" / "jersey_detection_yv8.pt"


def find_best_model():
    """尋找最佳模型"""
    runs_dir = CURRENT_DIR / "runs" / "jersey_detection"
    
    # 檢查 runs/jersey_detection 目錄是否存在
    if not runs_dir.exists():
        return None
    
    # 直接檢查 weights 目錄
    weights_dir = runs_dir / "weights"
    best_model = weights_dir / "best.pt"
    
    if best_model.exists():
        return best_model
    
    # 如果沒有找到，嘗試尋找子目錄（兼容舊結構）
    training_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name != "weights"]
    if training_dirs:
        latest_dir = max(training_dirs, key=lambda x: x.stat().st_mtime)
        best_model = latest_dir / "weights" / "best.pt"
        if best_model.exists():
            return best_model
    
    return None


def copy_model():
    """複製模型到專案"""
    print("=" * 60)
    print("整合球衣號碼檢測模型到排球分析專案")
    print("=" * 60)
    
    # 尋找最佳模型
    print("\n正在尋找訓練好的模型...")
    best_model = find_best_model()
    
    if not best_model:
        print("✗ 錯誤: 找不到訓練好的模型")
        print("請先運行 train_model.py 訓練模型")
        return False
    
    print(f"✓ 找到模型: {best_model}")
    
    # 檢查目標專案目錄
    if not PROJECT_DIR.exists():
        print(f"\n⚠️  警告: 找不到專案目錄: {PROJECT_DIR}")
        print("請確認專案路徑是否正確，或手動調整此腳本中的 PROJECT_DIR")
        return False
    
    print(f"✓ 找到專案目錄: {PROJECT_DIR}")
    
    # 創建 models 目錄（如果不存在）
    models_dir = PROJECT_DIR / "models"
    models_dir.mkdir(exist_ok=True)
    
    # 複製模型
    print(f"\n正在複製模型...")
    print(f"  來源: {best_model}")
    print(f"  目標: {MODEL_DEST}")
    
    try:
        shutil.copy2(best_model, MODEL_DEST)
        print(f"✓ 模型複製成功!")
        return True
    except Exception as e:
        print(f"✗ 複製失敗: {e}")
        return False


def create_integration_example():
    """創建整合範例代碼"""
    example_code = '''"""
球衣號碼檢測模組
使用 YOLOv8 模型檢測球衣號碼
"""

from ultralytics import YOLO
from pathlib import Path
import cv2
import numpy as np

class JerseyNumberDetector:
    """球衣號碼檢測器"""
    
    def __init__(self, model_path: str = None):
        """
        初始化檢測器
        
        Args:
            model_path: 模型文件路徑，如果為 None 則使用預設路徑
        """
        if model_path is None:
            model_path = Path(__file__).parent.parent / "models" / "jersey_detection_yv8.pt"
        
        self.model = YOLO(str(model_path))
        self.confidence_threshold = 0.25
        
    def detect(self, image: np.ndarray, conf: float = None):
        """
        檢測圖片中的球衣號碼
        
        Args:
            image: 輸入圖片 (BGR format)
            conf: 置信度閾值，如果為 None 則使用預設值
        
        Returns:
            list: 檢測結果列表，每個結果包含:
                - bbox: 邊界框 [x1, y1, x2, y2]
                - confidence: 置信度
                - class_id: 類別ID（球衣號碼）
                - number: 球衣號碼字符串
        """
        if conf is None:
            conf = self.confidence_threshold
        
        # 執行檢測
        results = self.model(image, conf=conf, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 獲取邊界框
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # 獲取置信度和類別
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                
                # 獲取類別名稱（球衣號碼）
                number = result.names[class_id]
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': confidence,
                    'class_id': class_id,
                    'number': number
                })
        
        return detections
    
    def detect_in_player_bbox(self, image: np.ndarray, player_bbox: list, conf: float = None):
        """
        在球員邊界框內檢測球衣號碼
        這是一個便利方法，用於從球員檢測結果中提取球衣號碼
        
        Args:
            image: 完整圖片
            player_bbox: 球員邊界框 [x1, y1, x2, y2]
            conf: 置信度閾值
        
        Returns:
            list: 檢測到的球衣號碼列表
        """
        x1, y1, x2, y2 = player_bbox
        
        # 裁剪球員區域（可以稍微擴大邊界框以包含球衣）
        padding = 20
        h, w = image.shape[:2]
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        
        player_roi = image[y1:y2, x1:x2]
        
        if player_roi.size == 0:
            return []
        
        # 在 ROI 中檢測
        detections = self.detect(player_roi, conf)
        
        # 調整座標到原圖
        for det in detections:
            det['bbox'][0] += x1
            det['bbox'][1] += y1
            det['bbox'][2] += x1
            det['bbox'][3] += y1
        
        return detections


# 使用範例
if __name__ == "__main__":
    # 初始化檢測器
    detector = JerseyNumberDetector()
    
    # 讀取圖片
    image_path = "path/to/your/image.jpg"
    image = cv2.imread(image_path)
    
    if image is None:
        print("無法讀取圖片")
        exit(1)
    
    # 檢測球衣號碼
    detections = detector.detect(image)
    
    # 顯示結果
    print(f"檢測到 {len(detections)} 個球衣號碼:")
    for det in detections:
        print(f"  號碼: {det['number']}, 置信度: {det['confidence']:.2f}, "
              f"位置: {det['bbox']}")
    
    # 在圖片上繪製結果
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, f"{det['number']} ({det['confidence']:.2f})",
                   (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    # 保存結果
    cv2.imwrite("result.jpg", image)
    print("結果已保存到 result.jpg")
'''
    
    example_path = CURRENT_DIR / "integration_example.py"
    with open(example_path, 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    print(f"\n✓ 創建整合範例代碼: {example_path}")
    return example_path


def main():
    """主函數"""
    success = copy_model()
    
    if success:
        print("\n" + "=" * 60)
        print("整合完成!")
        print("=" * 60)
        print(f"\n模型已複製到: {MODEL_DEST}")
        print("\n下一步:")
        print("1. 在您的專案中創建一個新的模組來使用此模型")
        print("2. 替換現有的 OCR 球衣號碼檢測代碼")
        print("3. 參考 integration_example.py 中的範例代碼")
        
        # 創建範例代碼
        create_integration_example()


if __name__ == "__main__":
    main()

