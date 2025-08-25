#!/bin/bash
# 智能餵料系統安裝腳本
# 適用於 Ubuntu 20.04 LTS (Jetson Nano)

set -e  # 遇到錯誤立即退出

echo "=================================================="
echo "智能水產養殖自動餵料控制系統 - 安裝腳本"
echo "=================================================="

# 檢查是否為root用戶
if [[ $EUID -eq 0 ]]; then
   echo "❌ 請不要使用root用戶執行此腳本"
   exit 1
fi

# 檢查系統版本
echo "🔍 檢查系統版本..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    echo "檢測到系統: $OS $VER"
    
    if [[ "$OS" != "Ubuntu" ]] || [[ "$VER" != "20.04" ]]; then
        echo "⚠️  警告: 本腳本針對 Ubuntu 20.04 優化，其他版本可能需要手動調整"
        read -p "是否繼續安裝? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "❌ 無法檢測系統版本"
    exit 1
fi

# 更新系統
echo "📦 更新系統套件..."
sudo apt update && sudo apt upgrade -y

# 安裝基礎依賴
echo "🛠️  安裝基礎依賴..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    cmake \
    build-essential \
    pkg-config \
    libopencv-dev \
    python3-opencv \
    libyaml-dev \
    libffi-dev \
    libssl-dev

# 檢查ROS2是否已安裝
echo "🤖 檢查ROS2安裝狀態..."
if [ -f "/opt/ros/foxy/setup.bash" ]; then
    echo "✅ 檢測到ROS2 Foxy"
    source /opt/ros/foxy/setup.bash
else
    echo "❌ 未檢測到ROS2 Foxy"
    echo "是否要安裝ROS2 Foxy? (推薦)"
    read -p "(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 安裝ROS2 Foxy..."
        
        # 添加ROS2官方源
        sudo apt install -y curl gnupg2 lsb-release
        curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
        
        # 安裝ROS2
        sudo apt update
        sudo apt install -y ros-foxy-desktop python3-rosdep2
        
        # 初始化rosdep
        sudo rosdep init
        rosdep update
        
        # 設置環境
        echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
        source /opt/ros/foxy/setup.bash
        
        echo "✅ ROS2 Foxy 安裝完成"
    fi
fi

# 檢查是否為Jetson平台
echo "🔧 檢查硬體平台..."
if [ -f "/etc/nv_tegra_release" ]; then
    echo "✅ 檢測到Jetson平台"
    JETSON_PLATFORM=true
    
    # 安裝Jetson GPIO
    echo "📌 安裝Jetson GPIO..."
    sudo pip3 install Jetson.GPIO
    
    # 添加用戶到gpio組
    sudo groupadd -f gpio
    sudo usermod -a -G gpio $USER
    
    echo "⚠️  需要重新登入或重啟以使GPIO權限生效"
else
    echo "ℹ️  非Jetson平台，將使用模擬模式"
    JETSON_PLATFORM=false
fi

# 建立專案目錄
PROJECT_DIR="$HOME/aquaFeederAutoAdj"
if [ -d "$PROJECT_DIR" ]; then
    echo "📁 專案目錄已存在: $PROJECT_DIR"
    read -p "是否要備份現有目錄並重新安裝? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mv "$PROJECT_DIR" "${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        echo "✅ 已備份舊目錄"
    else
        echo "❌ 安裝已取消"
        exit 1
    fi
fi

# 複製專案文件
echo "📋 複製專案文件..."
cp -r "$(pwd)" "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 建立虛擬環境
echo "🐍 建立Python虛擬環境..."
python3 -m venv venv
source venv/bin/activate

# 升級pip
pip install --upgrade pip

# 安裝Python依賴
echo "📦 安裝Python依賴..."
pip install -r requirements.txt

# 建立必要目錄
echo "📁 建立系統目錄..."
mkdir -p logs data debug_output

# 設置權限
echo "🔐 設置文件權限..."
chmod +x start_system.py
chmod +x install.sh

# 如果是ROS2環境，編譯專案
if [ -f "/opt/ros/foxy/setup.bash" ]; then
    echo "🔨 編譯ROS2專案..."
    source /opt/ros/foxy/setup.bash
    
    # 安裝ROS2依賴
    rosdep install --from-paths src --ignore-src -r -y || true
    
    # 編譯專案
    colcon build --packages-select aqua_feeder || echo "⚠️  ROS2編譯失敗，但可以使用獨立模式"
fi

# 創建桌面快捷方式
echo "🖥️  創建桌面快捷方式..."
DESKTOP_FILE="$HOME/Desktop/AquaFeeder.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=智能餵料系統
Comment=Smart Aquaculture Feeding System
Exec=gnome-terminal -- bash -c "cd $PROJECT_DIR && source venv/bin/activate && python3 start_system.py; read -p 'Press Enter to close...'"
Icon=$PROJECT_DIR/docs/icon.png
Terminal=true
Categories=Application;Science;
EOF

chmod +x "$DESKTOP_FILE"

# 設置環境變數
echo "🌍 設置環境變數..."
cat >> ~/.bashrc << EOF

# 智能餵料系統環境設定
export AQUA_FEEDER_HOME="$PROJECT_DIR"
export PYTHONPATH="\$AQUA_FEEDER_HOME/src:\$PYTHONPATH"
alias aqua-feeder="cd \$AQUA_FEEDER_HOME && source venv/bin/activate && python3 start_system.py"
alias aqua-logs="tail -f \$AQUA_FEEDER_HOME/logs/aqua_feeder_\$(date +%Y%m%d).log"
EOF

# 檢查相機
echo "📹 檢查相機連接..."
if [ -e /dev/video0 ]; then
    echo "✅ 檢測到相機設備 /dev/video0"
    # 設置相機權限
    sudo chmod 666 /dev/video0 || echo "⚠️  無法設置相機權限"
else
    echo "⚠️  未檢測到相機設備，請確認USB相機已連接"
fi

# 測試安裝
echo "🧪 測試系統安裝..."
source venv/bin/activate
python3 -c "
try:
    import cv2, numpy, yaml, scipy
    print('✅ 核心Python包測試通過')
except ImportError as e:
    print(f'❌ Python包測試失敗: {e}')
    exit(1)

try:
    from src.aqua_feeder.vision.image_processor import ImageProcessor
    print('✅ 系統模組載入測試通過')
except Exception as e:
    print(f'❌ 模組載入測試失敗: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ 系統測試通過"
else
    echo "❌ 系統測試失敗"
    exit 1
fi

# 安裝完成
echo ""
echo "=================================================="
echo "🎉 安裝完成!"
echo "=================================================="
echo "專案目錄: $PROJECT_DIR"
echo "虛擬環境: $PROJECT_DIR/venv"
echo ""
echo "啟動方式:"
echo "1. 桌面快捷方式: 雙擊 AquaFeeder 圖標"
echo "2. 終端命令: aqua-feeder"
echo "3. 手動啟動: cd $PROJECT_DIR && source venv/bin/activate && python3 start_system.py"
echo ""
echo "系統目錄:"
echo "- 配置文件: $PROJECT_DIR/config/system_params.yaml"
echo "- 日誌目錄: $PROJECT_DIR/logs/"
echo "- 資料目錄: $PROJECT_DIR/data/"
echo ""
echo "重要提醒:"
if [ "$JETSON_PLATFORM" = true ]; then
    echo "- 請重新登入或重啟系統以使GPIO權限生效"
fi
echo "- 首次使用前請閱讀 README.md"
echo "- 確保相機和硬體正確連接"
echo "- 根據實際環境調整配置參數"
echo ""
echo "技術支援: team@aquafeeder.com"
echo "文檔資源: $PROJECT_DIR/docs/"
echo "=================================================="

# 詢問是否立即重啟
if [ "$JETSON_PLATFORM" = true ]; then
    echo ""
    read -p "是否立即重啟系統以使所有設定生效? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在重啟系統..."
        sudo reboot
    else
        echo "請稍後手動重啟系統"
    fi
fi

echo "感謝使用智能餵料系統! 🐟"
