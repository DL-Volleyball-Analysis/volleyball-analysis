# 快速參考指南

## Windows 命令快速參考

### 設置環境變數（臨時）

**命令提示字元 (CMD):**
```cmd
set ROBOFLOW_API_KEY=your_api_key_here
```

**PowerShell:**
```powershell
$env:ROBOFLOW_API_KEY="your_api_key_here"
```

### 激活虛擬環境

```cmd
venv\Scripts\activate
```

### 檢查 CUDA

```cmd
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'N/A')"
```

### 完整流程命令

```cmd
REM 1. 激活虛擬環境
venv\Scripts\activate

REM 2. 設置 API Key（如果未永久設置）
set ROBOFLOW_API_KEY=your_api_key_here

REM 3. 下載資料集
python download_datasets.py

REM 4. 組織資料集
python organize_datasets.py

REM 5. 訓練模型
python train_model.py
```

## 常見問題快速解決

### CUDA 不可用？
```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 記憶體不足？
在 `train_model.py` 中修改 `batch_size = 16` 或更小

### 下載失敗？
確認 API Key 已設置：
```cmd
echo %ROBOFLOW_API_KEY%
```

