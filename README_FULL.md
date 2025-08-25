# 🐟 智能水產養殖自動餵料控制系統

## 🎯 項目概述
基於 Jetson Nano 和 ROS2 的智能餵料系統，通過視覺分析魚群活躍度來自動調節餵料量。

**✨ 現已完成美觀且功能完整的GUI界面，支援PC端模擬測試！**

## 🖥️ GUI界面展示

### 主要功能
- 🎮 **完整的圖形控制界面** - 直觀的系統操作
- 📊 **實時數據監控** - H值、PWM、特徵值即時顯示  
- 📈 **多維度圖表分析** - 時序圖、相關性分析、分布統計
- ⚙️ **參數即時調整** - 滑桿調節系統參數
- 🎯 **模擬模式支援** - PC端完整測試環境
- 📋 **配置管理** - 友好的參數配置界面
- 📊 **數據分析工具** - 日誌查看與統計分析

## 🚀 快速開始

### Windows用戶（推薦）
```bash
# 1. Enhanced GUI (新功能 - 支援相機畫面，ASCII輸出)
start_enhanced.bat

# 2. 或使用命令行啟動增強版
python launch_enhanced.py

# 3. 快速測試增強版GUI
python test_enhanced_gui.py

# 4. 原版GUI
start.bat
python launch_gui.py
```

### Linux/Mac用戶
```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 啟動增強版GUI
python launch_enhanced.py

# 3. 原版GUI
python launch_gui.py
```

### 📱 啟動選項說明
```bash
# Enhanced GUI (推薦)
python launch_enhanced.py         # 增強版啟動器
python test_enhanced_gui.py       # 直接啟動增強版GUI

# Original GUI
python launch_gui.py              # 原版啟動器  
python launch_gui.py --main-gui   # 直接啟動主GUI
python launch_gui.py --config     # 配置編輯器
python launch_gui.py --log        # 日誌查看器
python test_gui.py                # 系統測試
```

## 🎨 GUI組件介紹

### 🌟 **增強版GUI** (`enhanced_gui.py`) - **NEW!**
- **ASCII安全輸出**: 完全英文界面，解決中文亂碼問題
- **相機畫面顯示**: 實時視頻流與魚群行為模擬
- **系統控制區**: 啟動/停止、模式選擇（模擬/硬體）
- **相機控制區**: 相機啟動/停止、狀態顯示
- **實時數據區**: H值、PWM、特徵值數值顯示
- **參數調整區**: 滑桿即時調整H_hi、H_lo、Kp、Ki
- **手動控制區**: PWM手動輸出、手動餵食功能
- **圖表分析區**: 
  - 主要圖表：H值與PWM時序圖
  - 特徵分析：ME、RSI、POP、FLOW變化圖
- **狀態指示**: 系統、相機、PWM狀態燈號

### 1. 原版主控制界面 (`main_gui.py`)
- **系統控制區**: 啟動/停止、模式選擇
- **狀態監控區**: 實時狀態指示燈
- **數據顯示區**: H值、PWM、特徵值實時更新
- **參數調整區**: 滑桿即時調整H_hi、H_lo、Kp、Ki等參數
- **手動控制區**: PWM手動輸出、手動餵食功能
- **圖表分析區**: 
  - 主要圖表：H值與PWM時序圖
  - 特徵分析：ME、RSI、POP、FLOW變化圖
  - 系統分析：相關性與性能指標

### 2. 系統模擬器 (`simulator.py`)
- **真實環境模擬**: 魚群活躍度變化
- **特徵生成**: ME、RSI、POP、FLOW模擬數據
- **控制響應**: PI控制器實時響應
- **狀態機**: 餵食/評估/穩定狀態轉換

### 3. 配置編輯器 (`config_editor.py`)
- **分類配置頁面**:
  - 硬體配置：PWM、相機、GPIO設定
  - 控制配置：時間參數、門檻值、PI控制器
  - 視覺配置：CLAHE、ROI區域設定
  - 特徵配置：融合權重、正規化參數
  - 驗證配置：驗證門檻、測試參數
- **文件管理**: 載入/保存YAML/JSON配置

### 4. 日誌查看器 (`log_viewer.py`)
- **多格式支援**: CSV、Excel、文本文件
- **時間篩選**: 最近1小時/6小時/24小時/全部
- **統計分析**: 相關係數、振盪分析、命中率計算
- **圖表顯示**:
  - 時序分析：H值、PWM、特徵值時間變化
  - 相關性分析：散點圖、相關矩陣
  - 分布分析：直方圖、箱線圖

## 🔧 技術棧

### 硬體平台
- **主控**: Jetson Nano + Ubuntu 20.04 LTS
- **相機**: 1080p/60fps 單鏡頭攝影模組
- **控制**: PWM可調餵料馬達 (20%-70%)
- **照明**: 6500K LED高棚燈
- **展示**: 氣泡盤 + 打氣機 (8檔可調)

### 軟體框架
- **系統**: ROS2 Foxy + Python 3.8+
- **視覺**: OpenCV + NumPy + SciPy
- **GUI**: tkinter + matplotlib
- **數據**: pandas + YAML
- **控制**: 自研PI控制器 + 特徵融合算法

## 🧠 核心算法

### 特徵提取
1. **ME (Motion Energy)**: 動態能量計算
2. **RSI (Ripple Spectral Index)**: 波紋頻譜指數
3. **POP (Bubble Pop Events)**: 破泡事件檢測
4. **FLOW (Optical Flow)**: 光流不一致度

### 特徵融合公式
```
H = α·RSI + β·POP + γ·FLOW - δ·ME_ring
```
**預設權重**: α=0.4, β=0.3, γ=0.2, δ=0.1

### 控制策略
- **狀態機**: 餵食(0.6s)/評估(3.0s)/穩定(1.0s)
- **PI控制**: Kp=15.0, Ki=2.0, 含Anti-windup
- **門檻控制**: H_hi=0.65, H_lo=0.35
- **斜率限制**: PWM變化率限制

## 📊 系統驗證

### 性能指標
✅ **相關係數**: r(H, PWM) ≥ 0.75  
✅ **PWM振盪**: 振盪幅度 ≤ ±15%  
✅ **反應時間**: 故障降級 ≤ 1秒  
✅ **命中率**: T_disappear ≥ 70%  

### 自動化測試
```bash
# 完整系統測試
python test_gui.py

# 系統驗證
python -m aqua_feeder.validation.system_validator \
    --csv_file logs/feeding_data.csv
```

## 📁 項目結構

```
aquaFeederAutoAdj/
├── 🚀 launch_gui.py             # GUI啟動器
├── 🧪 test_gui.py               # 系統測試  
├── 🪟 start.bat                 # Windows啟動
├── ⚙️ config/
│   └── system_params.yaml      # 系統配置
├── 🎨 gui/                      # GUI組件
│   ├── main_gui.py             # 主控制界面
│   ├── simulator.py            # 系統模擬器
│   ├── config_editor.py        # 配置編輯器
│   ├── log_viewer.py           # 日誌查看器
│   └── README.md               # GUI使用說明
├── 🧠 src/aqua_feeder/          # 核心模塊
│   ├── vision/                 # 視覺處理
│   ├── control/                # 控制邏輯
│   ├── hardware/               # 硬體接口
│   └── validation/             # 系統驗證
├── 📊 logs/                     # 日誌輸出
├── 📚 docs/                     # 完整文檔
└── 🧪 tests/                    # 測試文件
```

## 💡 使用場景

### 🔬 研發模式
```bash
# 啟動模擬模式進行算法開發
python launch_gui.py --main-gui
# 選擇「模擬模式」-> 啟動系統 -> 調整參數觀察效果
```

### 🏭 硬體部署
```bash
# 在Jetson Nano上運行
# 選擇「硬體模式」-> 連接實際相機和PWM控制器
```

### 📈 數據分析
```bash
# 分析歷史運行數據
python launch_gui.py --log
# 載入CSV日誌文件 -> 查看統計分析和圖表
```

## 🎯 特色功能

### ✨ 實時互動
- 🎛️ 參數滑桿即時調整，立即看到效果
- 📊 多頁圖表同步更新，全方位監控
- 🎮 手動控制模式，支援PWM直接輸出

### 🎨 美觀界面
- 🖼️ 現代化GUI設計，操作直觀
- 📈 高質量matplotlib圖表
- 🚥 狀態指示燈實時顯示系統狀態

### 🔧 完整功能
- ⚙️ 參數配置系統，支援匯入/匯出
- 📊 數據分析工具，統計報告生成
- 🧪 系統測試模式，確保運行正常

## 🛠️ 故障排除

### 🔍 系統檢查
```bash
python test_gui.py  # 檢查所有組件狀態
```

### 📦 依賴安裝
```bash
pip install -r requirements.txt  # 安裝所有依賴
```

### 🐛 常見問題
1. **GUI無法啟動** → 檢查Python 3.8+和tkinter
2. **圖表不顯示** → 檢查matplotlib後端
3. **模擬器無響應** → 重啟主GUI
4. **配置載入失敗** → 檢查YAML格式

## 📈 開發進度

- ✅ **硬體物料清單** - 完整的BOM設計
- ✅ **軟體功能模塊** - 6大核心模塊全部實現  
- ✅ **參數配置系統** - 完整的配置管理
- ✅ **驗證測試框架** - 4項性能指標驗證
- ✅ **GUI界面系統** - 美觀且功能完整
- ✅ **模擬測試環境** - PC端完整測試支援
- ✅ **文檔體系** - 詳細的使用說明

## 🎉 立即體驗

1. **快速啟動**：
   ```bash
   python launch_gui.py
   ```

2. **選擇「啟動主要GUI」**

3. **選擇「模擬模式」並啟動系統**

4. **觀察實時數據和圖表變化**

5. **調整參數體驗系統響應**

**🎊 現在就可以在您的PC上完整體驗智能餵料控制系統！**

---

## 📚 更多信息

- 📖 [GUI詳細使用說明](gui/README.md)
- 📋 [功能模塊對應說明](docs/功能模塊對應說明.md)  
- 📊 [系統實現完成報告](docs/系統實現完成報告.md)

**開發團隊**: Aqua Feeder Team | **版本**: v1.0 | **年份**: 2025
