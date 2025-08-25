@echo off
title Advanced Aqua Feeder Control System v2.0
chcp 65001 > nul

echo ============================================================
echo  Advanced Aqua Feeder Control System v2.0
echo ============================================================
echo  New Features:
echo  * Scrollable interface - unlimited parameter controls
echo  * Real-time and simulation mode support
echo  * Auto-tuning capabilities
echo  * Enhanced data visualization
echo  * Configuration management
echo ============================================================

python launch_advanced.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Advanced GUI failed. Trying enhanced version...
    python launch_enhanced.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo Enhanced GUI failed. Trying basic version...
        python launch_gui.py
    )
)

echo.
echo Press any key to exit...
pause > nul
