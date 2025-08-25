"""
PI控制器
實現比例-積分控制算法，用於PWM輸出控制
"""

import time
import logging
from typing import Optional

class PIController:
    """PI控制器類"""
    
    def __init__(self, kp: float = 1.0, ki: float = 0.0, 
                 output_min: float = 0.0, output_max: float = 100.0,
                 anti_windup: bool = True, max_integral: float = 50.0):
        """
        初始化PI控制器
        
        Args:
            kp: 比例增益
            ki: 積分增益
            output_min: 輸出最小值
            output_max: 輸出最大值
            anti_windup: 是否啟用積分飽和保護
            max_integral: 最大積分值
        """
        self.kp = kp
        self.ki = ki
        self.output_min = output_min
        self.output_max = output_max
        self.anti_windup = anti_windup
        self.max_integral = max_integral
        
        # 控制器狀態
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = None
        
        self.logger = logging.getLogger(__name__)
        
    def update(self, setpoint: float, measured_value: float) -> float:
        """
        更新控制器並計算輸出
        
        Args:
            setpoint: 設定值
            measured_value: 測量值
            
        Returns:
            控制器輸出
        """
        current_time = time.time()
        
        # 計算誤差
        error = setpoint - measured_value
        
        # 計算時間間隔
        if self.last_time is None:
            dt = 0.1  # 預設時間間隔
        else:
            dt = current_time - self.last_time
            
        # 避免除零
        if dt <= 0:
            dt = 0.01
            
        # 比例項
        proportional = self.kp * error
        
        # 積分項
        self.integral += error * dt
        
        # 積分飽和保護
        if self.anti_windup:
            if self.integral > self.max_integral:
                self.integral = self.max_integral
            elif self.integral < -self.max_integral:
                self.integral = -self.max_integral
        
        integral_term = self.ki * self.integral
        
        # 計算總輸出
        output = proportional + integral_term
        
        # 輸出限制
        if output > self.output_max:
            output = self.output_max
            # 防止積分項繼續增長
            if self.anti_windup and error > 0:
                self.integral -= error * dt
        elif output < self.output_min:
            output = self.output_min
            # 防止積分項繼續減小
            if self.anti_windup and error < 0:
                self.integral -= error * dt
                
        # 更新狀態
        self.last_error = error
        self.last_time = current_time
        
        return output
    
    def reset(self):
        """重置控制器狀態"""
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = None
        self.logger.info("PI控制器已重置")
    
    def set_parameters(self, kp: Optional[float] = None, ki: Optional[float] = None):
        """
        設定控制器參數
        
        Args:
            kp: 比例增益
            ki: 積分增益
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
            
        self.logger.info(f"PI參數更新: Kp={self.kp}, Ki={self.ki}")
    
    def get_status(self) -> dict:
        """
        獲取控制器狀態
        
        Returns:
            狀態字典
        """
        return {
            'kp': self.kp,
            'ki': self.ki,
            'integral': self.integral,
            'last_error': self.last_error,
            'output_range': [self.output_min, self.output_max],
            'anti_windup': self.anti_windup,
            'max_integral': self.max_integral
        }
