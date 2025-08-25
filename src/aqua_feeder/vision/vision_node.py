"""
視覺處理ROS2節點
負責影像處理和特徵提取
符合需求書的影像前處理模塊要求：
- CLAHE：局部對比增強
- 直方圖匹配：展示缸 → 實池顏色域對齊  
- ROI 切割：ROI_bub、ROI_ring
- 特徵提取：ME、RSI、POP、FLOW
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray, Header, String
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml
import os
import time
import logging
from typing import Dict, Optional, Tuple

from .image_processor import ImageProcessor
from .feature_extractor import FeatureExtractor

class VisionNode(Node):
    """
    視覺處理節點
    實現需求書的影像前處理模塊功能
    """
    
    def __init__(self):
        super().__init__('vision_node')
        
        # 設定日誌
        self.logger = self.get_logger()
        
        # 載入配置
        self.config = self._load_config()
        
        # 初始化處理器
        vision_config = self.config.get('vision', {})
        self.image_processor = ImageProcessor(vision_config)
        self.feature_extractor = FeatureExtractor(self.config)
        
        # CV Bridge
        self.bridge = CvBridge()
        
        # 發布者
        self.feature_publisher = self.create_publisher(
            Float32MultiArray, 
            'aqua_feeder/features', 
            10
        )
        
        self.status_publisher = self.create_publisher(
            String,
            'aqua_feeder/vision_status',
            10
        )
        
        self.debug_image_publisher = self.create_publisher(
            Image,
            'aqua_feeder/debug_image',
            10
        )
        
        # 訂閱者
        self.image_subscriber = self.create_subscription(
            Image,
            'camera/image_raw',
            self.image_callback,
            10
        )
        
        # 計時器 - 用於定期發布狀態
        self.status_timer = self.create_timer(1.0, self.publish_status)
        
        # 狀態變數
        self.frame_count = 0
        self.last_features = {}
        
        self.logger.info("視覺處理節點初始化完成")
    
    def _load_config(self):
        """載入配置文件"""
        try:
            # 尋找配置文件
            config_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'system_params.yaml'),
                'config/system_params.yaml',
                '/opt/aqua_feeder/config/system_params.yaml'
            ]
            
            config_file = None
            for path in config_paths:
                if os.path.exists(path):
                    config_file = path
                    break
            
            if config_file is None:
                self.logger.warning("找不到配置文件，使用預設配置")
                return self._get_default_config()
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            self.logger.info(f"載入配置文件: {config_file}")
            return config
            
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """獲取預設配置"""
        return {
            'vision': {
                'roi_config': {
                    'roi_bub': {'x': 400, 'y': 300, 'width': 320, 'height': 240},
                    'roi_ring': {'x': 200, 'y': 150, 'width': 720, 'height': 480}
                },
                'preprocessing': {
                    'clahe': {'clip_limit': 2.0, 'tile_grid_size': [8, 8]},
                    'histogram_matching': {'enable': False}
                },
                'feature_extraction': {
                    'motion_energy': {'temporal_window': 5, 'threshold': 15},
                    'ripple_spectral': {'high_freq_start': 0.3, 'low_freq_end': 0.1},
                    'bubble_pop': {'min_area': 50, 'max_area': 500, 'circularity_threshold': 0.7},
                    'optical_flow': {'pyramid_levels': 3, 'window_size': 15}
                }
            },
            'feature_fusion': {
                'baseline': {'ME0': 10.0, 'RSI0': 0.2},
                'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
            }
        }
    
    def image_callback(self, msg):
        """影像回調函數"""
        try:
            # 轉換ROS影像為OpenCV格式
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
            # 影像前處理
            processed_image, rois = self.image_processor.preprocess_image(cv_image)
            
            # 特徵提取
            features = self.feature_extractor.extract_features(rois)
            
            # 發布特徵
            self._publish_features(features, msg.header.stamp)
            
            # 發布調試影像（如果啟用）
            self._publish_debug_image(processed_image, rois, features, msg.header)
            
            # 更新統計
            self.frame_count += 1
            self.last_features = features
            
        except Exception as e:
            self.logger.error(f"影像處理錯誤: {e}")
    
    def _publish_features(self, features, timestamp):
        """發布特徵向量"""
        try:
            msg = Float32MultiArray()
            msg.data = [
                float(features.get('RSI', 0.0)),
                float(features.get('POP', 0.0)),
                float(features.get('FLOW', 0.0)),
                float(features.get('ME_ring', 0.0)),
                float(features.get('ME', 0.0))
            ]
            
            self.feature_publisher.publish(msg)
            
        except Exception as e:
            self.logger.error(f"特徵發布錯誤: {e}")
    
    def _publish_debug_image(self, processed_image, rois, features, header):
        """發布調試影像"""
        try:
            # 創建調試影像
            debug_image = self._create_debug_image(processed_image, rois, features)
            
            # 轉換為ROS影像消息
            debug_msg = self.bridge.cv2_to_imgmsg(debug_image, "bgr8")
            debug_msg.header = header
            
            self.debug_image_publisher.publish(debug_msg)
            
        except Exception as e:
            self.logger.error(f"調試影像發布錯誤: {e}")
    
    def _create_debug_image(self, processed_image, rois, features):
        """創建調試影像"""
        # 轉換為彩色影像
        if len(processed_image.shape) == 2:
            debug_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2BGR)
        else:
            debug_image = processed_image.copy()
        
        # 繪製ROI框
        for roi_name in ['roi_bub', 'roi_ring']:
            coords = self.image_processor.get_roi_coordinates(roi_name)
            if coords:
                x, y, w, h = coords
                color = (0, 255, 0) if roi_name == 'roi_bub' else (0, 0, 255)
                cv2.rectangle(debug_image, (x, y), (x + w, y + h), color, 2)
                cv2.putText(debug_image, roi_name, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 添加特徵信息
        y_offset = 30
        for feature_name, value in features.items():
            text = f"{feature_name}: {value:.3f}"
            cv2.putText(debug_image, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        return debug_image
    
    def publish_status(self):
        """發布節點狀態"""
        self.logger.info(f"視覺節點運行中 - 處理幀數: {self.frame_count}")
        if self.last_features:
            feature_str = ", ".join([f"{k}:{v:.3f}" for k, v in self.last_features.items()])
            self.logger.debug(f"最新特徵: {feature_str}")

def main(args=None):
    """主函數"""
    rclpy.init(args=args)
    
    try:
        vision_node = VisionNode()
        rclpy.spin(vision_node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"視覺節點錯誤: {e}")
    finally:
        if 'vision_node' in locals():
            vision_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
