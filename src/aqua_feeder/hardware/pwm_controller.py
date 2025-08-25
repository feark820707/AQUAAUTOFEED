"""
PWM控制器
負責PWM可調餵料馬達/甩料器的控制
符合需求書：PWM可調餵料馬達/甩料器，PWM範圍20%-70%，線性控制
"""

import time
import logging
from typing import Optional

try:
    import Jetson.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("警告: Jetson.GPIO 不可用，使用模擬模式")
    GPIO_AVAILABLE = False
    # 開發環境模擬
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        
        @staticmethod
        def setmode(mode): pass
        
        @staticmethod
        def setup(pin, mode): pass
        
        @staticmethod
        def PWM(pin, freq): return MockPWM()
        
        @staticmethod
        def cleanup(): pass
    
    class MockPWM:
        def start(self, duty): pass
        def stop(self): pass
        def ChangeDutyCycle(self, duty): pass
    
    GPIO = MockGPIO()

class PWMController:
    """PWM控制器類 - 符合需求書規格"""
    
    def __init__(self, config: dict):
        """
        初始化PWM控制器
        
        Args:
            config: 硬體配置字典，包含PWM參數
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # PWM配置 - 符合需求書規格
        pwm_config = config.get('pwm', {})
        self.gpio_pin = pwm_config.get('gpio_pin', 18)
        self.frequency = pwm_config.get('frequency', 1000)  # 1kHz
        self.min_duty = pwm_config.get('min_duty_cycle', 20)  # 20%最小值
        self.max_duty = pwm_config.get('max_duty_cycle', 70)  # 70%最大值
        
        # PWM對象
        self.pwm = None
        self.current_duty = self.min_duty
        self.is_initialized = False
        self.is_running = False
        
        # 初始化GPIO
        self._initialize_gpio()
    
    def _initialize_gpio(self):
        """
        初始化GPIO和PWM
        符合需求書的控制板（MOSFET/驅動模組）要求
        """
        try:
            if GPIO_AVAILABLE:
                # 設定GPIO模式
                GPIO.setmode(GPIO.BCM)
                
                # 設定引腳為輸出
                GPIO.setup(self.gpio_pin, GPIO.OUT)
                
                # 創建PWM對象
                self.pwm = GPIO.PWM(self.gpio_pin, self.frequency)
            else:
                # 模擬模式
                self.pwm = GPIO.PWM(self.gpio_pin, self.frequency)
            
            self.is_initialized = True
            self.logger.info(f"PWM控制器初始化成功:")
            self.logger.info(f"  GPIO引腳: {self.gpio_pin}")
            self.logger.info(f"  頻率: {self.frequency} Hz")
            self.logger.info(f"  占空比範圍: {self.min_duty}%-{self.max_duty}%")
            
        except Exception as e:
            self.logger.error(f"PWM初始化失敗: {e}")
            self.is_initialized = False
    
    def start(self, initial_duty: Optional[float] = None):
        """
        啟動PWM輸出
        
        Args:
            initial_duty: 初始占空比，默認使用最小值
        """
        if not self.is_initialized:
            self.logger.error("PWM控制器未正確初始化")
            return False
        
        if self.is_running:
            self.logger.warning("PWM已在運行")
            return True
        
        try:
            # 使用指定的初始占空比或默認最小值
            duty = initial_duty if initial_duty is not None else self.min_duty
            duty = self._clamp_duty_cycle(duty)
            
            # 啟動PWM
            self.pwm.start(duty)
            self.current_duty = duty
            self.is_running = True
            
            self.logger.info(f"PWM啟動，初始占空比: {duty}%")
            return True
            
        except Exception as e:
            self.logger.error(f"PWM啟動失敗: {e}")
            return False
    
    def stop(self):
        """停止PWM輸出"""
        if not self.is_running:
            return
        
        try:
            self.pwm.stop()
            self.is_running = False
            self.logger.info("PWM已停止")
            
        except Exception as e:
            self.logger.error(f"PWM停止失敗: {e}")
    
    def set_duty_cycle(self, duty_cycle: float) -> bool:
        """
        設定PWM占空比
        實現線性控制，符合需求書20%-70%範圍要求
        
        Args:
            duty_cycle: 目標占空比 (%)
            
        Returns:
            設定是否成功
        """
        if not self.is_running:
            self.logger.error("PWM未運行，無法設定占空比")
            return False
        
        try:
            # 限制占空比在允許範圍內
            clamped_duty = self._clamp_duty_cycle(duty_cycle)
            
            # 更新PWM
            self.pwm.ChangeDutyCycle(clamped_duty)
            
            # 記錄變化
            if abs(clamped_duty - self.current_duty) > 0.1:
                self.logger.debug(f"PWM占空比變化: {self.current_duty:.1f}% -> {clamped_duty:.1f}%")
            
            self.current_duty = clamped_duty
            return True
            
        except Exception as e:
            self.logger.error(f"設定PWM占空比失敗: {e}")
            return False
    
    def _clamp_duty_cycle(self, duty_cycle: float) -> float:
        """
        限制占空比在允許範圍內
        確保符合需求書的20%-70%限制
        
        Args:
            duty_cycle: 輸入占空比
            
        Returns:
            限制後的占空比
        """
        if duty_cycle < self.min_duty:
            self.logger.warning(f"占空比 {duty_cycle}% 低於最小值，調整為 {self.min_duty}%")
            return self.min_duty
        elif duty_cycle > self.max_duty:
            self.logger.warning(f"占空比 {duty_cycle}% 高於最大值，調整為 {self.max_duty}%")
            return self.max_duty
        else:
            return duty_cycle
    
    def get_current_duty_cycle(self) -> float:
        """
        獲取當前占空比
        
        Returns:
            當前占空比 (%)
        """
        return self.current_duty
    
    def test_pwm_linearity(self, test_points: int = 10, delay: float = 0.5) -> dict:
        """
        測試PWM線性度
        符合需求書的PWM線性測試要求
        
        Args:
            test_points: 測試點數量
            delay: 每個測試點間隔時間
            
        Returns:
            測試結果字典
        """
        if not self.is_running:
            self.logger.error("PWM未運行，無法進行線性度測試")
            return {}
        
        test_results = {
            'test_points': [],
            'start_time': time.time(),
            'success': False
        }
        
        try:
            original_duty = self.current_duty
            
            # 生成測試點
            step = (self.max_duty - self.min_duty) / (test_points - 1)
            test_duties = [self.min_duty + i * step for i in range(test_points)]
            
            self.logger.info(f"開始PWM線性度測試，測試點數: {test_points}")
            
            for i, target_duty in enumerate(test_duties):
                test_start = time.time()
                
                # 設定目標占空比
                success = self.set_duty_cycle(target_duty)
                
                # 記錄測試點
                test_point = {
                    'index': i,
                    'target_duty': target_duty,
                    'actual_duty': self.current_duty,
                    'success': success,
                    'timestamp': test_start,
                    'error': abs(target_duty - self.current_duty)
                }
                
                test_results['test_points'].append(test_point)
                
                if delay > 0:
                    time.sleep(delay)
            
            # 恢復原始占空比
            self.set_duty_cycle(original_duty)
            
            # 計算線性度統計
            errors = [point['error'] for point in test_results['test_points']]
            test_results.update({
                'max_error': max(errors),
                'avg_error': sum(errors) / len(errors),
                'linearity_score': 1.0 - (max(errors) / (self.max_duty - self.min_duty)),
                'success': True,
                'end_time': time.time()
            })
            
            self.logger.info(f"PWM線性度測試完成:")
            self.logger.info(f"  最大誤差: {test_results['max_error']:.2f}%")
            self.logger.info(f"  平均誤差: {test_results['avg_error']:.2f}%")
            self.logger.info(f"  線性度分數: {test_results['linearity_score']:.3f}")
            
        except Exception as e:
            self.logger.error(f"PWM線性度測試失敗: {e}")
            test_results['error'] = str(e)
        
        return test_results
    
    def emergency_stop(self):
        """
        緊急停止
        立即將PWM設為安全值
        """
        try:
            if self.is_running:
                # 設為最小安全值
                self.pwm.ChangeDutyCycle(self.min_duty)
                self.current_duty = self.min_duty
                self.logger.warning("執行緊急停止，PWM設為最小值")
            
        except Exception as e:
            self.logger.error(f"緊急停止失敗: {e}")
    
    def cleanup(self):
        """清理GPIO資源"""
        try:
            if self.is_running:
                self.stop()
            
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            self.is_initialized = False
            self.logger.info("PWM控制器資源已清理")
            
        except Exception as e:
            self.logger.error(f"PWM清理失敗: {e}")
    
    def get_status(self) -> dict:
        """
        獲取PWM控制器狀態
        
        Returns:
            狀態字典
        """
        return {
            'gpio_pin': self.gpio_pin,
            'frequency': self.frequency,
            'duty_range': [self.min_duty, self.max_duty],
            'current_duty': self.current_duty,
            'is_initialized': self.is_initialized,
            'is_running': self.is_running
        }
    
    def __del__(self):
        """析構函數"""
        self.cleanup()
    
    def start(self, initial_duty: float = 0.0):
        """
        啟動PWM輸出
        
        Args:
            initial_duty: 初始占空比 (%)
        """
        if self.pwm is not None and GPIO_AVAILABLE:
            try:
                # 限制占空比範圍
                duty = max(self.min_duty, min(self.max_duty, initial_duty))
                
                self.pwm.start(duty)
                self.current_duty = duty
                self.is_running = True
                
                self.logger.info(f"PWM啟動 - 占空比: {duty:.1f}%")
            except Exception as e:
                self.logger.error(f"PWM啟動失敗: {e}")
        else:
            # 模擬模式
            duty = max(self.min_duty, min(self.max_duty, initial_duty))
            self.current_duty = duty
            self.is_running = True
            self.logger.info(f"PWM模擬啟動 - 占空比: {duty:.1f}%")
    
    def set_duty_cycle(self, duty: float):
        """
        設定占空比
        
        Args:
            duty: 占空比 (%)
        """
        if not self.is_running:
            self.logger.warning("PWM未啟動，無法設定占空比")
            return
        
        # 限制占空比範圍
        duty = max(self.min_duty, min(self.max_duty, duty))
        
        if self.pwm is not None and GPIO_AVAILABLE:
            try:
                self.pwm.ChangeDutyCycle(duty)
                self.current_duty = duty
                self.logger.debug(f"PWM占空比更新: {duty:.1f}%")
            except Exception as e:
                self.logger.error(f"PWM占空比設定失敗: {e}")
        else:
            # 模擬模式
            self.current_duty = duty
            self.logger.debug(f"PWM模擬占空比: {duty:.1f}%")
    
    def set_frequency(self, frequency: int):
        """
        設定PWM頻率
        
        Args:
            frequency: 頻率 (Hz)
        """
        if self.pwm is not None and GPIO_AVAILABLE:
            try:
                self.pwm.ChangeFrequency(frequency)
                self.frequency = frequency
                self.logger.info(f"PWM頻率更新: {frequency}Hz")
            except Exception as e:
                self.logger.error(f"PWM頻率設定失敗: {e}")
        else:
            # 模擬模式
            self.frequency = frequency
            self.logger.info(f"PWM模擬頻率: {frequency}Hz")
    
    def stop(self):
        """停止PWM輸出"""
        if self.pwm is not None and GPIO_AVAILABLE:
            try:
                self.pwm.stop()
                self.is_running = False
                self.current_duty = 0.0
                self.logger.info("PWM已停止")
            except Exception as e:
                self.logger.error(f"PWM停止失敗: {e}")
        else:
            # 模擬模式
            self.is_running = False
            self.current_duty = 0.0
            self.logger.info("PWM模擬停止")
    
    def cleanup(self):
        """清理GPIO資源"""
        self.stop()
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup(self.pin)
                self.logger.info("GPIO資源已清理")
            except Exception as e:
                self.logger.error(f"GPIO清理失敗: {e}")
    
    def get_status(self) -> dict:
        """
        獲取PWM狀態
        
        Returns:
            狀態字典
        """
        return {
            'pin': self.pin,
            'frequency': self.frequency,
            'current_duty': self.current_duty,
            'duty_range': [self.min_duty, self.max_duty],
            'is_running': self.is_running,
            'gpio_available': GPIO_AVAILABLE
        }
    
    def __del__(self):
        """析構函數"""
        self.cleanup()
