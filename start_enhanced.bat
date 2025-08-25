@echo off
title Aqua Feeder Control System - Enhanced Version
chcp 65001 > nul

echo ======================================================
echo  Aqua Feeder Control System v1.0 Enhanced
echo ======================================================
echo  Starting enhanced GUI with camera support...
echo  ASCII safe output - No encoding issues
echo ======================================================

python launch_enhanced.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred. Trying fallback launcher...
    python launch_gui.py
)

echo.
echo Press any key to exit...
pause > nul
