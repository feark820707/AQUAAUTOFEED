"""
控制節點
實現需求書的控制器模塊功能：
- 分段控制（H_hi/H_lo）
- PI控制器（Kp, Ki）
- 斜率限制 Δup, Δdown
- Anti-windup（反積分）
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, Float32, String
import yaml
import os
import time
import csv
from datetime import datetime
import logging
from typing import Dict, Optional

from .feeding_controller import FeedingController, FeedingState

class ControlNode(Node):
    """
    控制節點
    實現需求書的控制器模塊功能
    """
    
    def __init__(self):
        super().__init__('control_node')
        
        # 設定日誌
        self.logger = self.get_logger()
        
        # 載入配置
        self.config = self._load_config()
        
        # 初始化控制器 - 符合需求書規格
        self.feeding_controller = FeedingController(self.config)
        
        # 發布者
        self.pwm_publisher = self.create_publisher(
            Float32,
            'aqua_feeder/pwm_command',
            10
        )
        
        self.status_publisher = self.create_publisher(
            String,
            'aqua_feeder/control_status',
            10
        )
        
        # 訂閱者 - 接收特徵向量
        self.feature_subscriber = self.create_subscription(
            Float32MultiArray,
            'aqua_feeder/features',
            self.feature_callback,
            10
        )
        
        # 發布者 - 發送PWM命令
        self.pwm_publisher = self.create_publisher(
            Float32,
            'aqua_feeder/pwm_command',
            10
        )
        
        # 發布者 - 控制狀態
        self.status_publisher = self.create_publisher(
            Float32MultiArray,
            'aqua_feeder/control_status',
            10
        )
        
        # 定時器 - 定期發布狀態
        self.status_timer = self.create_timer(1.0, self.publish_status)
        
        # 狀態變數
        self.current_fps = 60.0
        self.last_pwm = 20.0
        
        self.logger.info("控制節點初始化完成")
    
    def _load_config(self):
        """載入配置文件"""
        try:
            # 嘗試從不同位置載入配置
            config_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'system_params.yaml'),
                'config/system_params.yaml',
                '/opt/aqua_feeder/config/system_params.yaml'
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    self.logger.info(f"載入配置文件: {path}")
                    return config
            
            # 如果找不到配置文件，使用預設配置
            self.logger.warning("找不到配置文件，使用預設配置")
            return self._get_default_config()
            
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """獲取預設配置"""
        return {
            'controller': {
                'timing': {'t_feed': 0.6, 't_eval': 3.0, 't_settle': 1.0},
                'thresholds': {'H_hi': 0.65, 'H_lo': 0.35},
                'pi_controller': {'Kp': 15.0, 'Ki': 2.0},
                'constraints': {'delta_up': 10.0, 'delta_down': 15.0},
                'anti_windup': {'enable': True, 'max_integral': 50.0}
            },
            'feature_fusion': {
                'weights': {'alpha': 0.4, 'beta': 0.3, 'gamma': 0.2, 'delta': 0.1},
                'baseline': {'ME0': 10.0, 'RSI0': 0.2},
                'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
            },
            'hardware': {'pwm': {'min_duty_cycle': 20, 'max_duty_cycle': 70}},
            'anomaly_detection': {
                'fps_threshold': 50,
                'fallback_mode': {'pwm_safe_value': 30}
            }
        }
    
    def feature_callback(self, msg):
        """特徵向量回調函數"""
        try:
            # 解析特徵向量 [RSI, POP, FLOW, ME_ring, ME]
            if len(msg.data) >= 5:
                features = {
                    'RSI': float(msg.data[0]),
                    'POP': float(msg.data[1]),
                    'FLOW': float(msg.data[2]),
                    'ME_ring': float(msg.data[3]),
                    'ME': float(msg.data[4])
                }
                
                # 更新控制器
                pwm, state = self.feeding_controller.update(features, self.current_fps)
                
                # 發布PWM命令
                pwm_msg = Float32()
                pwm_msg.data = float(pwm)
                self.pwm_publisher.publish(pwm_msg)
                
                self.last_pwm = pwm
                
                self.logger.debug(f"控制更新: PWM={pwm:.1f}, 狀態={state.value}")
                
            else:
                self.logger.warning(f"特徵向量長度不足: {len(msg.data)}")
                
        except Exception as e:
            self.logger.error(f"特徵處理錯誤: {e}")
    
    def publish_status(self):
        """發布控制狀態"""
        try:
            status = self.feeding_controller.get_status()
            
            # 創建狀態消息 [PWM, H_target, state_enum, time_in_state]
            status_msg = Float32MultiArray()
            status_msg.data = [
                float(status['current_pwm']),
                float(status['target_H']),
                float(hash(status['state']) % 100),  # 狀態枚舉值
                float(status['time_in_state'])
            ]
            
            self.status_publisher.publish(status_msg)
            
        except Exception as e:
            self.logger.error(f"狀態發布錯誤: {e}")

def main(args=None):
    """主函數"""
    rclpy.init(args=args)
    
    try:
        control_node = ControlNode()
        rclpy.spin(control_node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"控制節點錯誤: {e}")
    finally:
        if 'control_node' in locals():
            control_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
