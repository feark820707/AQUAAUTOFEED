"""
餵料控制器
整合特徵融合、PI控制、異常檢測等功能
"""

import time
import logging
from typing import Dict, Optional, Tuple
from enum import Enum
from .pi_controller import PIController

class FeedingState(Enum):
    """餵料狀態"""
    INIT = "初始化"
    FEEDING = "餵食中"
    EVALUATING = "評估中"
    SETTLING = "穩定等待"
    ANOMALY = "異常模式"
    PAUSED = "暫停"

class FeedingController:
    """餵料控制器主類"""
    
    def __init__(self, config: dict):
        """
        初始化餵料控制器
        
        Args:
            config: 系統配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 提取控制器配置
        ctrl_config = config.get('controller', {})
        
        # 時間參數
        timing = ctrl_config.get('timing', {})
        self.t_feed = timing.get('t_feed', 0.6)
        self.t_eval = timing.get('t_eval', 3.0)
        self.t_settle = timing.get('t_settle', 1.0)
        
        # 閾值參數
        thresholds = ctrl_config.get('thresholds', {})
        self.H_hi = thresholds.get('H_hi', 0.65)
        self.H_lo = thresholds.get('H_lo', 0.35)
        
        # PWM約束
        constraints = ctrl_config.get('constraints', {})
        self.delta_up = constraints.get('delta_up', 10.0)
        self.delta_down = constraints.get('delta_down', 15.0)
        
        # 特徵融合權重
        fusion_config = config.get('feature_fusion', {})
        weights = fusion_config.get('weights', {})
        self.alpha = weights.get('alpha', 0.4)  # RSI權重
        self.beta = weights.get('beta', 0.3)    # POP權重
        self.gamma = weights.get('gamma', 0.2)  # FLOW權重
        self.delta = weights.get('delta', 0.1)  # ME_ring權重（負貢獻）
        
        # 正規化參數
        norm_config = fusion_config.get('normalization', {})
        self.RSI_max = norm_config.get('RSI_max', 2.0)
        self.POP_max = norm_config.get('POP_max', 10.0)
        self.FLOW_max = norm_config.get('FLOW_max', 100.0)
        self.ME_max = norm_config.get('ME_max', 50.0)
        
        # 基線值
        baseline = fusion_config.get('baseline', {})
        self.ME0 = baseline.get('ME0', 10.0)
        self.RSI0 = baseline.get('RSI0', 0.2)
        
        # 初始化PI控制器
        pi_config = ctrl_config.get('pi_controller', {})
        hardware_config = config.get('hardware', {}).get('pwm', {})
        pwm_min = hardware_config.get('min_duty_cycle', 20)
        pwm_max = hardware_config.get('max_duty_cycle', 70)
        
        anti_windup_config = ctrl_config.get('anti_windup', {})
        
        self.pi_controller = PIController(
            kp=pi_config.get('Kp', 15.0),
            ki=pi_config.get('Ki', 2.0),
            output_min=pwm_min,
            output_max=pwm_max,
            anti_windup=anti_windup_config.get('enable', True),
            max_integral=anti_windup_config.get('max_integral', 50.0)
        )
        
        # 控制器狀態
        self.state = FeedingState.INIT
        self.current_pwm = pwm_min
        self.target_H = (self.H_hi + self.H_lo) / 2  # 目標活躍度
        
        # 時間追蹤
        self.state_start_time = time.time()
        self.last_update_time = time.time()
        
        # 異常檢測
        self.anomaly_config = config.get('anomaly_detection', {})
        self.low_activity_start = None
        self.fps_below_threshold_start = None
        
        self.logger.info("餵料控制器初始化完成")
    
    def update(self, features: Dict[str, float], fps: float) -> Tuple[float, FeedingState]:
        """
        更新控制器狀態和PWM輸出
        
        Args:
            features: 特徵字典 {'RSI': float, 'POP': float, 'FLOW': float, 'ME_ring': float}
            fps: 當前幀率
            
        Returns:
            Tuple[新的PWM值, 當前狀態]
        """
        current_time = time.time()
        
        # 檢查異常情況
        if self._check_anomalies(features, fps, current_time):
            return self.current_pwm, self.state
        
        # 計算活躍度H值
        H = self._calculate_activity_index(features)
        
        # 狀態機邏輯
        self._update_state_machine(H, current_time)
        
        # 根據狀態更新PWM
        new_pwm = self._update_pwm_output(H)
        
        self.last_update_time = current_time
        
        return new_pwm, self.state
    
    def _calculate_activity_index(self, features: Dict[str, float]) -> float:
        """
        計算活躍度指數H
        
        Args:
            features: 特徵字典
            
        Returns:
            活躍度指數H (0-1)
        """
        # 提取並正規化特徵
        RSI = min(features.get('RSI', self.RSI0) / self.RSI_max, 1.0)
        POP = min(features.get('POP', 0.0) / self.POP_max, 1.0)
        FLOW = min(features.get('FLOW', 0.0) / self.FLOW_max, 1.0)
        ME_ring = min(features.get('ME_ring', self.ME0) / self.ME_max, 1.0)
        
        # 融合計算
        H = self.alpha * RSI + self.beta * POP + self.gamma * FLOW - self.delta * ME_ring
        
        # 確保H在合理範圍內
        H = max(0.0, min(1.0, H))
        
        return H
    
    def _update_state_machine(self, H: float, current_time: float):
        """
        更新狀態機
        
        Args:
            H: 當前活躍度
            current_time: 當前時間
        """
        time_in_state = current_time - self.state_start_time
        
        if self.state == FeedingState.INIT:
            self.state = FeedingState.FEEDING
            self.state_start_time = current_time
            
        elif self.state == FeedingState.FEEDING:
            if time_in_state >= self.t_feed:
                self.state = FeedingState.EVALUATING
                self.state_start_time = current_time
                
        elif self.state == FeedingState.EVALUATING:
            if time_in_state >= self.t_eval:
                self.state = FeedingState.SETTLING
                self.state_start_time = current_time
                
        elif self.state == FeedingState.SETTLING:
            if time_in_state >= self.t_settle:
                self.state = FeedingState.FEEDING
                self.state_start_time = current_time
                
        elif self.state == FeedingState.ANOMALY:
            # 異常模式下的恢復邏輯
            pass
    
    def _update_pwm_output(self, H: float) -> float:
        """
        更新PWM輸出
        
        Args:
            H: 當前活躍度
            
        Returns:
            新的PWM值
        """
        if self.state == FeedingState.EVALUATING:
            # 評估階段使用PI控制器
            target_H = self.target_H
            pi_output = self.pi_controller.update(target_H, H)
            
            # 應用變化幅度限制
            delta = pi_output - self.current_pwm
            
            if delta > 0:
                delta = min(delta, self.delta_up)
            else:
                delta = max(delta, -self.delta_down)
            
            new_pwm = self.current_pwm + delta
            
            # 確保在硬體範圍內
            pwm_min = self.pi_controller.output_min
            pwm_max = self.pi_controller.output_max
            new_pwm = max(pwm_min, min(pwm_max, new_pwm))
            
            self.current_pwm = new_pwm
            
        elif self.state == FeedingState.ANOMALY:
            # 異常模式使用安全值
            safe_pwm = self.anomaly_config.get('fallback_mode', {}).get('pwm_safe_value', 30)
            self.current_pwm = safe_pwm
        
        return self.current_pwm
    
    def _check_anomalies(self, features: Dict[str, float], fps: float, current_time: float) -> bool:
        """
        檢查異常情況
        
        Args:
            features: 特徵字典
            fps: 當前幀率
            current_time: 當前時間
            
        Returns:
            是否檢測到異常
        """
        # 檢查FPS過低
        fps_threshold = self.anomaly_config.get('fps_threshold', 50)
        if fps < fps_threshold:
            if self.fps_below_threshold_start is None:
                self.fps_below_threshold_start = current_time
            elif current_time - self.fps_below_threshold_start > 1.0:  # 1秒後切換
                self.state = FeedingState.ANOMALY
                self.logger.warning(f"FPS過低 ({fps:.1f}) - 切換至異常模式")
                return True
        else:
            self.fps_below_threshold_start = None
        
        # 檢查持續低活躍度
        H = self._calculate_activity_index(features)
        low_activity_duration = self.anomaly_config.get('low_activity_duration', 30)
        
        if H < self.H_lo * 0.5:  # 極低活躍度
            if self.low_activity_start is None:
                self.low_activity_start = current_time
            elif current_time - self.low_activity_start > low_activity_duration:
                # 延長評估時間
                extension = self.anomaly_config.get('fallback_mode', {}).get('evaluation_extension', 2.0)
                self.t_eval = self.t_eval * extension
                self.low_activity_start = None
                self.logger.warning(f"持續低活躍度 - 延長評估時間至 {self.t_eval:.1f}s")
        else:
            self.low_activity_start = None
        
        return False
    
    def reset(self):
        """重置控制器狀態"""
        self.state = FeedingState.INIT
        self.pi_controller.reset()
        self.state_start_time = time.time()
        self.low_activity_start = None
        self.fps_below_threshold_start = None
        
        # 重置時間參數
        timing = self.config.get('controller', {}).get('timing', {})
        self.t_eval = timing.get('t_eval', 3.0)
        
        self.logger.info("餵料控制器已重置")
    
    def get_status(self) -> dict:
        """獲取控制器狀態信息"""
        return {
            'state': self.state.value,
            'current_pwm': self.current_pwm,
            'target_H': self.target_H,
            'time_in_state': time.time() - self.state_start_time,
            'timing': {
                't_feed': self.t_feed,
                't_eval': self.t_eval,
                't_settle': self.t_settle
            },
            'thresholds': {
                'H_hi': self.H_hi,
                'H_lo': self.H_lo
            },
            'pi_status': self.pi_controller.get_status()
        }
