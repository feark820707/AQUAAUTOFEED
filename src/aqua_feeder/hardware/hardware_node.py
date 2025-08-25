"""
硬體節點
ROS2硬體接口節點，處理PWM控制和GPIO操作
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Float32MultiArray
import yaml
import os
import logging

from .pwm_controller import PWMController
from .gpio_controller import GPIOController

class HardwareNode(Node):
    """硬體接口節點"""
    
    def __init__(self):
        super().__init__('hardware_node')
        
        # 設定日誌
        self.logger = self.get_logger()
        
        # 載入配置
        self.config = self._load_config()
        
        # 初始化硬體控制器
        self._init_hardware()
        
        # 訂閱者 - 接收PWM命令
        self.pwm_subscriber = self.create_subscription(
            Float32,
            'aqua_feeder/pwm_command',
            self.pwm_callback,
            10
        )
        
        # 發布者 - 硬體狀態
        self.status_publisher = self.create_publisher(
            Float32MultiArray,
            'aqua_feeder/hardware_status',
            10
        )
        
        # 定時器 - 定期發布狀態
        self.status_timer = self.create_timer(2.0, self.publish_status)
        
        self.logger.info("硬體節點初始化完成")
    
    def _load_config(self):
        """載入配置文件"""
        try:
            config_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'system_params.yaml'),
                'config/system_params.yaml'
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    self.logger.info(f"載入配置文件: {path}")
                    return config
            
            self.logger.warning("找不到配置文件，使用預設配置")
            return self._get_default_config()
            
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """獲取預設配置"""
        return {
            'hardware': {
                'pwm': {
                    'gpio_pin': 18,
                    'frequency': 1000,
                    'min_duty_cycle': 20,
                    'max_duty_cycle': 70
                },
                'led_lighting': {
                    'gpio_pin': 19,
                    'brightness': 80
                },
                'airflow_simulator': {
                    'gpio_pins': [20, 21, 22],
                    'default_level': 0
                }
            }
        }
    
    def _init_hardware(self):
        """初始化硬體控制器"""
        try:
            # 初始化PWM控制器
            pwm_config = self.config.get('hardware', {}).get('pwm', {})
            self.pwm_controller = PWMController(
                pin=pwm_config.get('gpio_pin', 18),
                frequency=pwm_config.get('frequency', 1000),
                min_duty=pwm_config.get('min_duty_cycle', 20),
                max_duty=pwm_config.get('max_duty_cycle', 70)
            )
            
            # 啟動PWM
            self.pwm_controller.start(pwm_config.get('min_duty_cycle', 20))
            
            # 初始化GPIO控制器
            self.gpio_controller = GPIOController(self.config)
            
            self.logger.info("硬體控制器初始化成功")
            
        except Exception as e:
            self.logger.error(f"硬體初始化失敗: {e}")
            self.pwm_controller = None
            self.gpio_controller = None
    
    def pwm_callback(self, msg):
        """PWM命令回調函數"""
        try:
            pwm_value = float(msg.data)
            
            if self.pwm_controller:
                self.pwm_controller.set_duty_cycle(pwm_value)
                self.logger.debug(f"PWM設定: {pwm_value:.1f}%")
            else:
                self.logger.warning("PWM控制器未初始化")
                
        except Exception as e:
            self.logger.error(f"PWM設定錯誤: {e}")
    
    def publish_status(self):
        """發布硬體狀態"""
        try:
            # 收集硬體狀態
            pwm_status = self.pwm_controller.get_status() if self.pwm_controller else {}
            gpio_status = self.gpio_controller.get_status() if self.gpio_controller else {}
            
            # 創建狀態消息 [PWM占空比, PWM運行狀態, GPIO可用性, 錯誤計數]
            status_msg = Float32MultiArray()
            status_msg.data = [
                float(pwm_status.get('current_duty', 0.0)),
                float(1.0 if pwm_status.get('is_running', False) else 0.0),
                float(1.0 if pwm_status.get('gpio_available', False) else 0.0),
                float(0.0)  # 錯誤計數 (可以後續實現)
            ]
            
            self.status_publisher.publish(status_msg)
            
        except Exception as e:
            self.logger.error(f"狀態發布錯誤: {e}")
    
    def shutdown(self):
        """節點關閉清理"""
        try:
            if self.pwm_controller:
                self.pwm_controller.cleanup()
            if self.gpio_controller:
                self.gpio_controller.cleanup()
            self.logger.info("硬體資源已清理")
        except Exception as e:
            self.logger.error(f"清理錯誤: {e}")
    
    def __del__(self):
        """析構函數"""
        self.shutdown()

def main(args=None):
    """主函數"""
    rclpy.init(args=args)
    
    try:
        hardware_node = HardwareNode()
        rclpy.spin(hardware_node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"硬體節點錯誤: {e}")
    finally:
        if 'hardware_node' in locals():
            hardware_node.shutdown()
            hardware_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
