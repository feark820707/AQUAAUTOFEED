"""
硬體接口模塊
包含PWM控制、GPIO控制、感測器讀取等功能
"""

from .pwm_controller import PWMController
from .gpio_controller import GPIOController
from .camera_interface import CameraInterface
from .hardware_node import HardwareNode

# 主要對外接口
HardwareInterface = HardwareNode

__all__ = [
    'PWMController',
    'GPIOController',
    'CameraInterface',
    'HardwareNode',
    'HardwareInterface'
]
