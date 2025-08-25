# 智能水產養殖自動餵料控制系統

## 專案概述

本專案是一個基於Jetson Nano和ROS2的智能水產養殖自動餵料控制系統，通過視覺分析魚群活躍度來自動調節餵料量，實現精準餵食和資源優化。

## 系統架構

```
┌─────────────────────────┐    ┌─────────────────────────┐
│     硬體層 (Hardware)    │    │     感測器層 (Sensors)   │
├─────────────────────────┤    ├─────────────────────────┤
│ • Jetson Nano          │    │ • 1080p 攝影模組         │
│ • PWM 餵料馬達          │    │ • 6500K LED 照明         │
│ • MOSFET 控制板         │    │ • 氣泡盤（展示用）        │
│ • GPIO 接口            │    │ • 打氣機控制             │
└─────────────────────────┘    └─────────────────────────┘
           │                              │
           └──────────────┬───────────────┘
                         │
┌─────────────────────────┴─────────────────────────┐
│              軟體層 (Software Stack)              │
├───────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│ │ 視覺處理模組  │ │ 控制器模組   │ │ 硬體接口模組  │  │
│ │ • CLAHE     │ │ • PI控制器   │ │ • PWM控制    │  │
│ │ • 特徵提取   │ │ • 狀態機     │ │ • 相機接口    │  │
│ │ • ROI分析    │ │ • 異常檢測   │ │ • GPIO控制   │  │
│ └─────────────┘ └─────────────┘ └─────────────┘  │
└───────────────────────────────────────────────────┘
           │
┌─────────────────────────┴─────────────────────────┐
│                ROS2 Foxy                          │
│ • 節點間通訊 • 參數管理 • 生命週期管理               │
└───────────────────────────────────────────────────┘
```

## 主要功能特點

### 🎯 核心功能
- **智能視覺分析**: 基於OpenCV的實時影像處理
- **多特徵融合**: ME、RSI、POP、FLOW四維特徵提取
- **自適應控制**: PI控制器實現精準PWM調節
- **異常檢測**: 多層次安全機制與故障恢復
- **資料記錄**: 完整的CSV日誌與視覺化報表

### 🔧 技術特色
- **模塊化設計**: 高內聚低耦合的系統架構
- **實時性能**: 60fps影像處理與控制響應
- **容錯機制**: 硬體故障自動降級處理
- **參數可調**: YAML配置文件靈活調參
- **ROS2整合**: 標準化的機器人作業系統

## 硬體需求 (BOM)

### 核心組件
| 組件 | 規格 | 數量 | 備註 |
|-----|------|------|------|
| Jetson Nano | 4GB開發板 | 1 | 主控制器 |
| USB攝影模組 | 1080p@60fps | 1 | 具備俯視拍攝能力 |
| PWM餵料馬達 | 可調速甩料器 | 1 | 20-70%範圍線性控制 |
| LED高棚燈 | 6500K色溫 | 1 | 穩定照明光源 |
| MOSFET控制板 | 驅動模組 | 1 | PWM信號放大 |

### 展示組件
| 組件 | 規格 | 數量 | 用途 |
|-----|------|------|------|
| 氣泡盤 | 6檔可調 | 1 | 模擬魚咬活動 |
| 打氣機 | 靜音型 | 1 | 氣泡產生 |
| 黑/綠底襯布 | 高對比 | 1 | 背景優化 |
| 偏光鏡 | CPL | 1 | 減少反光 |

## 軟體安裝

### 前置需求
```bash
# Ubuntu 20.04 LTS (Jetson Nano)
# ROS2 Foxy
# Python 3.8+
```

### 1. 系統依賴安裝
```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝基礎依賴
sudo apt install -y python3-pip python3-venv git cmake build-essential

# 安裝OpenCV依賴
sudo apt install -y libopencv-dev python3-opencv

# 安裝ROS2 Foxy (如未安裝)
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-foxy-desktop python3-rosdep2
```

### 2. Python依賴安裝
```bash
# 進入專案目錄
cd aquaFeederAutoAdj

# 建立虛擬環境（可選）
python3 -m venv venv
source venv/bin/activate

# 安裝Python依賴
pip3 install -r requirements.txt
```

### 3. ROS2環境設定
```bash
# 初始化rosdep
sudo rosdep init
rosdep update

# 安裝ROS2依賴
rosdep install --from-paths src --ignore-src -r -y

# 編譯專案
colcon build --packages-select aqua_feeder

# 設定環境變數
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

## 系統配置

### 硬體安裝步驟

1. **環境準備**
   ```bash
   # 鋪設背景襯布，確保高對比度
   # 建議使用黑色或深綠色無反光材質
   ```

2. **相機架設**
   ```bash
   # 固定高度: 0.8-1.2m
   # 俯視角度: 垂直向下
   # CPL偏光鏡: 調整至最佳減反光角度
   ```

3. **照明調整**
   ```bash
   # 光源位置: 斜上方45°
   # 避免直射鏡頭造成眩光
   # 確保照明均勻穩定
   ```

4. **餵料器安裝**
   ```bash
   # 出料口對準ROI區域中心
   # PWM測試範圍: 20-70%
   # 確認線性響應特性
   ```

### 軟體配置

編輯 `config/system_params.yaml` 調整系統參數：

```yaml
# 相機參數調整
hardware:
  camera:
    device_id: 0          # USB相機設備ID
    resolution: [1920, 1080]
    fps: 60

# ROI區域設定
vision:
  roi_config:
    roi_bub:              # 氣泡檢測區域
      x: 400
      y: 300
      width: 320
      height: 240
    roi_ring:             # 環狀波紋檢測區域
      x: 200
      y: 150
      width: 720
      height: 480

# 控制器參數
controller:
  timing:
    t_feed: 0.6           # 餵食時間窗 (秒)
    t_eval: 3.0           # 評估時間窗 (秒)
  
  thresholds:
    H_hi: 0.65            # 高活躍度門檻
    H_lo: 0.35            # 低活躍度門檻
```

## 系統啟動

### 方式一: 一鍵啟動 (推薦)
```bash
# 啟動完整系統
python3 src/aqua_feeder/main_controller.py
```

### 方式二: ROS2節點啟動
```bash
# 啟動ROS2節點
ros2 launch aqua_feeder aqua_feeder_launch.py

# 或簡化版啟動
ros2 run aqua_feeder main_controller
```

### 方式三: 開發調試模式
```bash
# 分別啟動各節點 (適合開發調試)
ros2 run aqua_feeder vision_node
ros2 run aqua_feeder control_node  
ros2 run aqua_feeder hardware_node
```

## 操作指南

### 日常使用流程

1. **系統檢查**
   ```bash
   # 檢查硬體連接
   # 驗證相機影像
   # 確認照明條件
   ```

2. **啟動系統**
   ```bash
   python3 src/aqua_feeder/main_controller.py
   ```

3. **監控狀態**
   ```bash
   # 觀察控制台輸出
   # 檢查logs目錄下的CSV記錄
   # 監控PWM輸出變化
   ```

4. **系統停止**
   ```bash
   # 按 Ctrl+C 安全停止
   # 系統會自動清理資源
   ```

### ROI區域校正

使用調試模式校正檢測區域：

```bash
# 啟動視覺調試
python3 -c "
from src.aqua_feeder.vision.image_processor import ImageProcessor
import cv2
import yaml

# 載入配置
with open('config/system_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

processor = ImageProcessor(config)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if ret:
        processed, rois = processor.preprocess_image(frame)
        
        # 顯示ROI框
        for roi_name in ['roi_bub', 'roi_ring']:
            coords = processor.get_roi_coordinates(roi_name)
            if coords:
                x, y, w, h = coords
                color = (0, 255, 0) if roi_name == 'roi_bub' else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, roi_name, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv2.imshow('ROI Calibration', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
"
```

## 性能指標與驗證

### 目標性能指標

| 指標 | 目標值 | 驗證方法 |
|-----|-------|---------|
| 相關係數 r(airflow, H) | ≥ 0.75 | 展示缸氣泡盤對比測試 |
| PWM振盪幅度 | ≤ ±15% | 10迴合穩定性測試 |
| T_disappear命中率 | ≥ 70% | 統計分析餵食消失時間 |
| 故障反應時間 | ≤ 1.0s | 異常情境模擬測試 |

### 驗證測試

1. **相關性驗證**
   ```bash
   # 啟動展示模式
   python3 validation/correlation_test.py
   # 調整氣泡盤檔位，記錄H值變化
   # 計算相關係數
   ```

2. **穩定性測試**
   ```bash
   # 長時間運行測試
   python3 validation/stability_test.py --duration 3600
   # 分析PWM振盪幅度
   ```

3. **異常處理測試**
   ```bash
   # 模擬相機斷線
   python3 validation/anomaly_test.py --test camera_disconnect
   # 模擬低FPS情況
   python3 validation/anomaly_test.py --test low_fps
   ```

## 資料分析與報表

系統會自動產生以下記錄檔案：

### CSV日誌格式
```csv
timestamp,state,pwm,H,RSI,POP,FLOW,ME_ring,warnings
2024-08-25T10:30:15,餵食中,45.2,0.567,0.234,1.23,15.6,8.9,
2024-08-25T10:30:18,評估中,47.8,0.623,0.289,2.45,18.2,7.1,
```

### 日報表生成
```bash
# 生成日報表
python3 analysis/generate_daily_report.py --date 2024-08-25

# 產生圖表:
# 1. H值vs PWM趨勢圖
# 2. 活躍度時序圖  
# 3. 異常事件標註
```

## 故障排除

### 常見問題

**Q1: 相機無法啟動**
```bash
# 檢查設備連接
lsusb | grep -i camera

# 檢查權限
sudo chmod 666 /dev/video0

# 測試相機
python3 -c "import cv2; cap=cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Error')"
```

**Q2: PWM輸出無響應**
```bash
# 檢查GPIO權限
sudo usermod -a -G gpio $USER

# 重新登入或重啟
sudo reboot

# 測試GPIO
python3 -c "
try:
    import Jetson.GPIO as GPIO
    print('GPIO Library OK')
except ImportError:
    print('Install: sudo pip3 install Jetson.GPIO')
"
```

**Q3: 特徵值異常**
```bash
# 檢查照明條件
# 調整ROI區域
# 重新校正參考基線
```

### 日誌分析

檢查日誌文件獲取詳細錯誤信息：
```bash
# 系統日誌
tail -f logs/aqua_feeder_$(date +%Y%m%d).log

# CSV資料日誌
tail -f logs/feeding_log_$(date +%Y%m%d).csv

# 錯誤日誌過濾
grep -i error logs/aqua_feeder_$(date +%Y%m%d).log
```

## 開發指南

### 擴展新功能

1. **添加新的特徵提取器**
   ```python
   # 在 vision/feature_extractor.py 中添加新方法
   def _extract_new_feature(self, roi):
       # 實現新特徵算法
       return feature_value
   ```

2. **修改控制策略**
   ```python
   # 在 control/feeding_controller.py 中調整
   def _calculate_activity_index(self, features):
       # 修改特徵融合公式
       return H
   ```

3. **增加硬體接口**
   ```python
   # 在 hardware/ 目錄下添加新的硬體模組
   class NewHardwareInterface:
       def __init__(self, config):
           pass
   ```

### 貢獻代碼

1. Fork本專案
2. 創建功能分支
3. 提交代碼並添加測試
4. 發送Pull Request

## 授權許可

本專案採用 MIT 授權許可。詳見 [LICENSE](LICENSE) 文件。

## 聯絡支援

- 專案維護: AquaFeeder Team
- 技術支援: team@aquafeeder.com
- 問題回報: [GitHub Issues](https://github.com/aquafeeder/aquaFeederAutoAdj/issues)

## 更新日誌

### v1.0.0 (2024-08-25)
- 初始版本發布
- 完整的視覺處理管線
- PI控制器實現
- ROS2節點架構
- 資料記錄與分析功能

---

**注意**: 本系統需要在實際環境中進行校正和調參才能達到最佳性能。建議在部署前進行充分的測試驗證。
