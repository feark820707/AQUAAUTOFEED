"""
視覺處理模塊
包含影像前處理、特徵提取、特徵融合等功能
"""

from .image_processor import ImageProcessor
from .feature_extractor import FeatureExtractor
from .vision_node import VisionNode

# 主要對外接口
VisionProcessor = VisionNode

__all__ = [
    'ImageProcessor',
    'FeatureExtractor', 
    'VisionNode',
    'VisionProcessor'
]
