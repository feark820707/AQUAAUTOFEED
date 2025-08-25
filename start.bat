@echo off
chcp 65001 >nul
title 智能水產養殖自動餵料控制系統

echo.
echo ======================================================
echo     智能水產養殖自動餵料控制系統
echo     Intelligent Aquatic Feeding Control System
echo ======================================================
echo.

cd /d "%~dp0"

echo 正在檢查Python環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 錯誤: 未找到Python，請確保已安裝Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python環境檢查通過

echo.
echo 請選擇啟動模式:
echo   1. GUI啟動器 (推薦)
echo   2. 直接啟動主GUI
echo   3. 配置編輯器
echo   4. 日誌查看器
echo   5. 系統測試
echo   6. 安裝依賴
echo.

set /p choice="請輸入選項 (1-6): "

if "%choice%"=="1" (
    echo 啟動GUI啟動器...
    python launch_gui.py
) else if "%choice%"=="2" (
    echo 啟動主GUI...
    python launch_gui.py --main-gui
) else if "%choice%"=="3" (
    echo 啟動配置編輯器...
    python launch_gui.py --config
) else if "%choice%"=="4" (
    echo 啟動日誌查看器...
    python launch_gui.py --log
) else if "%choice%"=="5" (
    echo 運行系統測試...
    python test_gui.py
) else if "%choice%"=="6" (
    echo 安裝依賴...
    pip install -r requirements.txt
) else (
    echo 無效選項，啟動GUI啟動器...
    python launch_gui.py
)

echo.
echo 系統已退出，按任意鍵關閉...
pause >nul
