"""
智能水產養殖自動餵料控制系統
主包初始化文件
"""

__version__ = "1.0.0"
__author__ = "AquaFeeder Team"
__description__ = "智能水產養殖自動餵料控制系統"

# 導入主要模塊
from .vision import VisionProcessor
from .control import FeedingController
from .hardware import HardwareInterface

__all__ = [
    'VisionProcessor',
    'FeedingController', 
    'HardwareInterface'
]
