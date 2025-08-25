#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI模塊初始化文件

包含智能水產養殖自動餵料控制系統的所有GUI組件
"""

__version__ = "1.0.0"
__author__ = "Aqua Feeder Team"

# 模塊導入
try:
    from .main_gui import AquaFeederGUI
    from .simulator import SystemSimulator
    from .config_editor import ConfigEditor
    from .log_viewer import LogViewer
    
    __all__ = [
        'AquaFeederGUI',
        'SystemSimulator', 
        'ConfigEditor',
        'LogViewer'
    ]
    
except ImportError as e:
    print(f"GUI模塊導入警告: {e}")
    __all__ = []
