#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統模擬器 - 提供PC端測試用的模擬數據

模擬真實硬體環境的行為，包括：
- 魚群活躍度變化
- 特徵值波動
- PWM控制響應
- 系統狀態轉換
"""

import numpy as np
import time
import threading
import random
from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class FeedingState(Enum):
    """餵食狀態枚舉"""
    STOPPED = 0
    FEEDING = 1
    EVALUATING = 2
    SETTLING = 3


@dataclass
class SimulationParams:
    """模擬參數"""
    # 控制參數
    H_hi: float = 0.65
    H_lo: float = 0.35
    Kp: float = 15.0
    Ki: float = 2.0
    
    # 特徵融合權重
    alpha: float = 0.4
    beta: float = 0.3
    gamma: float = 0.2
    delta: float = 0.1
    
    # 時間參數
    t_feed: float = 0.6
    t_eval: float = 3.0
    t_settle: float = 1.0


class SystemSimulator:
    """系統模擬器類"""
    
    def __init__(self):
        self.params = SimulationParams()
        self.is_running = False
        self.thread = None
        
        # 系統狀態
        self.current_state = FeedingState.STOPPED
        self.state_start_time = 0
        
        # 實時數據
        self.current_data = {
            'H': 0.5,
            'PWM': 20.0,
            'FPS': 60,
            'ME': 0.3,
            'RSI': 0.4,
            'POP': 0.2,
            'FLOW': 0.1
        }
        
        # PI控制器狀態
        self.pi_integral = 0.0
        self.last_error = 0.0
        self.current_pwm = 20.0
        
        # 模擬環境
        self.fish_activity_base = 0.5  # 基礎活躍度
        self.feeding_effect = 0.0      # 餵食效果
        self.environmental_noise = 0.0 # 環境噪聲
        
        # 手動控制
        self.manual_pwm_override = None
        self.manual_feed_time = 0
        
        # 時間追蹤
        self.start_time = 0
        self.last_update_time = 0
        
        # 數據歷史（用於相關性計算）
        self.data_history = []
        
    def start(self):
        """啟動模擬器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.current_state = FeedingState.EVALUATING
        self.state_start_time = self.start_time
        
        # 啟動模擬線程
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """停止模擬器"""
        self.is_running = False
        self.current_state = FeedingState.STOPPED
        if self.thread:
            self.thread.join(timeout=1.0)
            
    def update_params(self, params: Dict[str, Any]):
        """更新模擬參數"""
        for key, value in params.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)
                
    def update_param(self, param: str, value: float):
        """更新單個參數"""
        if hasattr(self.params, param):
            setattr(self.params, param, value)
            
    def set_manual_pwm(self, pwm: float):
        """設置手動PWM輸出"""
        self.manual_pwm_override = np.clip(pwm, 20, 70)
        
    def clear_manual_pwm(self):
        """清除手動PWM覆蓋"""
        self.manual_pwm_override = None
        
    def trigger_manual_feed(self):
        """觸發手動餵食"""
        self.manual_feed_time = time.time()
        
    def get_current_data(self) -> Dict[str, float]:
        """獲取當前數據"""
        return self.current_data.copy()
        
    def get_current_state(self) -> int:
        """獲取當前狀態（數值形式）"""
        return self.current_state.value
        
    def _simulation_loop(self):
        """主要模擬循環"""
        while self.is_running:
            current_time = time.time()
            dt = current_time - self.last_update_time
            
            if dt >= 0.1:  # 100ms更新間隔
                self._update_simulation(current_time, dt)
                self.last_update_time = current_time
                
            time.sleep(0.01)  # 10ms休眠
            
    def _update_simulation(self, current_time: float, dt: float):
        """更新模擬狀態"""
        # 更新環境模擬
        self._update_environment(current_time, dt)
        
        # 生成模擬特徵
        self._generate_features(current_time)
        
        # 計算活躍度H
        H = self._calculate_activity_index()
        self.current_data['H'] = H
        
        # 更新狀態機
        self._update_state_machine(current_time, H)
        
        # 控制PWM輸出
        self._update_pwm_control(H, dt)
        
        # 更新其他數據
        self.current_data['FPS'] = 60 + random.uniform(-2, 2)
        
        # 記錄數據歷史
        self._record_data_history(current_time)
        
    def _update_environment(self, current_time: float, dt: float):
        """更新環境模擬"""
        # 基礎活躍度變化（模擬魚群自然活動模式）
        day_cycle = np.sin(2 * np.pi * (current_time - self.start_time) / 60)  # 1分鐘週期
        self.fish_activity_base = 0.5 + 0.2 * day_cycle
        
        # 餵食效果衰減
        if self.feeding_effect > 0:
            self.feeding_effect *= np.exp(-dt / 5.0)  # 5秒衰減時間常數
            
        # 手動餵食效果
        if self.manual_feed_time > 0 and (current_time - self.manual_feed_time) < 3.0:
            manual_effect = 0.3 * np.exp(-(current_time - self.manual_feed_time) / 2.0)
            self.feeding_effect = max(self.feeding_effect, manual_effect)
        elif self.manual_feed_time > 0 and (current_time - self.manual_feed_time) >= 3.0:
            self.manual_feed_time = 0
            
        # 環境噪聲
        self.environmental_noise = 0.1 * np.sin(2 * np.pi * current_time * 0.5) + \
                                  0.05 * random.uniform(-1, 1)
                                  
    def _generate_features(self, current_time: float):
        """生成模擬特徵值"""
        # 基礎活躍度
        base_activity = self.fish_activity_base + self.feeding_effect + self.environmental_noise
        base_activity = np.clip(base_activity, 0.1, 0.9)
        
        # ME (Motion Energy) - 與活躍度正相關
        me_base = 0.3 + 0.4 * base_activity
        me_noise = 0.05 * random.uniform(-1, 1)
        self.current_data['ME'] = np.clip(me_base + me_noise, 0.0, 1.0)
        
        # RSI (Ripple Spectral Index) - 模擬水面波紋
        rsi_base = 0.2 + 0.6 * base_activity
        rsi_ripple = 0.1 * np.sin(2 * np.pi * current_time * 2)  # 高頻波動
        self.current_data['RSI'] = np.clip(rsi_base + rsi_ripple, 0.0, 1.0)
        
        # POP (Bubble Pop Events) - 模擬破泡事件
        pop_base = 0.1 + 0.3 * base_activity
        # 隨機破泡事件
        if random.random() < 0.1:  # 10%機率產生破泡事件
            pop_base += 0.2
        self.current_data['POP'] = np.clip(pop_base, 0.0, 1.0)
        
        # FLOW (Optical Flow) - 模擬光流不一致度
        flow_base = 0.1 + 0.2 * base_activity
        flow_turbulence = 0.05 * random.uniform(-1, 1)
        self.current_data['FLOW'] = np.clip(flow_base + flow_turbulence, 0.0, 1.0)
        
    def _calculate_activity_index(self) -> float:
        """計算活躍度指數H"""
        # 從當前特徵計算H值
        RSI = self.current_data['RSI']
        POP = self.current_data['POP']
        FLOW = self.current_data['FLOW']
        ME = self.current_data['ME']
        
        # 特徵融合公式
        H = (self.params.alpha * RSI + 
             self.params.beta * POP + 
             self.params.gamma * FLOW - 
             self.params.delta * ME)
        
        return np.clip(H, 0.0, 1.0)
        
    def _update_state_machine(self, current_time: float, H: float):
        """更新狀態機"""
        state_duration = current_time - self.state_start_time
        
        if self.current_state == FeedingState.EVALUATING:
            if state_duration >= self.params.t_eval:
                if H >= self.params.H_hi:
                    # 高活躍度 -> 餵食
                    self.current_state = FeedingState.FEEDING
                    self.state_start_time = current_time
                elif H <= self.params.H_lo:
                    # 低活躍度 -> 穩定等待
                    self.current_state = FeedingState.SETTLING
                    self.state_start_time = current_time
                else:
                    # 中等活躍度 -> 繼續評估
                    self.state_start_time = current_time
                    
        elif self.current_state == FeedingState.FEEDING:
            if state_duration >= self.params.t_feed:
                # 餵食完成 -> 穩定等待
                self.current_state = FeedingState.SETTLING
                self.state_start_time = current_time
                # 添加餵食效果
                self.feeding_effect += 0.2
                
        elif self.current_state == FeedingState.SETTLING:
            if state_duration >= self.params.t_settle:
                # 穩定完成 -> 評估
                self.current_state = FeedingState.EVALUATING
                self.state_start_time = current_time
                
    def _update_pwm_control(self, H: float, dt: float):
        """更新PWM控制"""
        if self.manual_pwm_override is not None:
            # 手動控制模式
            self.current_pwm = self.manual_pwm_override
        else:
            # 自動控制模式
            if self.current_state == FeedingState.FEEDING:
                # 餵食期間使用PI控制器
                setpoint = 0.6  # 目標活躍度
                error = setpoint - H
                
                # PI控制計算
                proportional = self.params.Kp * error
                self.pi_integral += error * dt
                integral = self.params.Ki * self.pi_integral
                
                # Anti-windup
                if self.pi_integral > 10.0:
                    self.pi_integral = 10.0
                elif self.pi_integral < -10.0:
                    self.pi_integral = -10.0
                    
                # 計算輸出
                output = proportional + integral
                target_pwm = 20 + output
                
                # PWM限制
                target_pwm = np.clip(target_pwm, 20, 70)
                
                # 斜率限制
                delta = target_pwm - self.current_pwm
                if delta > 0:
                    delta = min(delta, 10.0 * dt)  # 上升限制
                else:
                    delta = max(delta, -15.0 * dt)  # 下降限制
                    
                self.current_pwm = self.current_pwm + delta
                
            else:
                # 非餵食期間保持最小PWM
                target_pwm = 20.0
                delta = target_pwm - self.current_pwm
                if abs(delta) > 0.1:
                    delta = np.sign(delta) * min(abs(delta), 5.0 * dt)
                    self.current_pwm += delta
                    
        # 更新PWM輸出數據
        self.current_data['PWM'] = np.clip(self.current_pwm, 20, 70)
        
    def _record_data_history(self, current_time: float):
        """記錄數據歷史"""
        data_point = {
            'timestamp': current_time,
            'H': self.current_data['H'],
            'PWM': self.current_data['PWM'],
            'state': self.current_state.value,
            'ME': self.current_data['ME'],
            'RSI': self.current_data['RSI'],
            'POP': self.current_data['POP'],
            'FLOW': self.current_data['FLOW']
        }
        
        self.data_history.append(data_point)
        
        # 限制歷史長度（保留最近1小時數據）
        max_history = 36000  # 1小時 * 3600秒 * 10點/秒
        if len(self.data_history) > max_history:
            self.data_history = self.data_history[-max_history:]
            
    def get_data_history(self) -> list:
        """獲取數據歷史"""
        return self.data_history.copy()
        
    def calculate_correlation(self) -> float:
        """計算H值與PWM的相關係數"""
        if len(self.data_history) < 100:
            return 0.0
            
        h_values = [d['H'] for d in self.data_history[-100:]]
        pwm_values = [d['PWM'] for d in self.data_history[-100:]]
        
        correlation = np.corrcoef(h_values, pwm_values)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
        
    def get_performance_metrics(self) -> Dict[str, float]:
        """獲取性能指標"""
        if len(self.data_history) < 100:
            return {
                'correlation': 0.0,
                'pwm_oscillation': 0.0,
                'response_time': 0.0,
                'uptime': time.time() - self.start_time if self.is_running else 0.0
            }
            
        # 相關係數
        correlation = self.calculate_correlation()
        
        # PWM振盪幅度
        recent_pwm = [d['PWM'] for d in self.data_history[-100:]]
        pwm_std = np.std(recent_pwm)
        pwm_oscillation = (pwm_std / np.mean(recent_pwm)) * 100  # 百分比
        
        # 系統運行時間
        uptime = time.time() - self.start_time if self.is_running else 0.0
        
        # 模擬反應時間（實際系統中會測量狀態轉換時間）
        response_time = 0.5 + random.uniform(-0.2, 0.2)
        
        return {
            'correlation': correlation,
            'pwm_oscillation': pwm_oscillation,
            'response_time': response_time,
            'uptime': uptime
        }
