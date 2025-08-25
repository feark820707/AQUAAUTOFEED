"""
GPIO控制器
負責LED照明和氣泡盤的GPIO控制
"""

import logging
from typing import List, Optional

try:
    import Jetson.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("警告: Jetson.GPIO 不可用，使用模擬模式")
    GPIO_AVAILABLE = False

class GPIOController:
    """GPIO控制器類"""
    
    def __init__(self, config: dict):
        """
        初始化GPIO控制器
        
        Args:
            config: 系統配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 提取GPIO配置
        hardware_config = config.get('hardware', {})
        
        # LED控制配置
        led_config = hardware_config.get('led_lighting', {})
        self.led_pin = led_config.get('gpio_pin', 19)
        self.led_brightness = led_config.get('brightness', 80)
        
        # 氣泡盤控制配置
        airflow_config = hardware_config.get('airflow_simulator', {})
        self.airflow_pins = airflow_config.get('gpio_pins', [20, 21, 22])
        self.airflow_level = airflow_config.get('default_level', 0)
        
        # 初始化GPIO
        self.gpio_initialized = False
        self._initialize_gpio()
    
    def _initialize_gpio(self):
        """初始化GPIO設定"""
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BOARD)
                
                # 設定LED控制引腳
                GPIO.setup(self.led_pin, GPIO.OUT)
                GPIO.output(self.led_pin, GPIO.HIGH)  # 預設開啟照明
                
                # 設定氣泡盤控制引腳
                for pin in self.airflow_pins:
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)  # 預設關閉
                
                self.gpio_initialized = True
                self.logger.info(f"GPIO初始化成功 - LED: {self.led_pin}, 氣泡盤: {self.airflow_pins}")
                
            except Exception as e:
                self.logger.error(f"GPIO初始化失敗: {e}")
                self.gpio_initialized = False
        else:
            # 模擬模式
            self.gpio_initialized = True
            self.logger.warning("GPIO模擬模式運行")
    
    def set_led_state(self, state: bool):
        """
        設定LED狀態
        
        Args:
            state: True為開啟，False為關閉
        """
        if not self.gpio_initialized:
            self.logger.warning("GPIO未初始化，無法控制LED")
            return
        
        if GPIO_AVAILABLE:
            try:
                GPIO.output(self.led_pin, GPIO.HIGH if state else GPIO.LOW)
                self.logger.info(f"LED {'開啟' if state else '關閉'}")
            except Exception as e:
                self.logger.error(f"LED控制失敗: {e}")
        else:
            # 模擬模式
            self.logger.info(f"LED模擬 {'開啟' if state else '關閉'}")
    
    def set_airflow_level(self, level: int):
        """
        設定氣泡盤檔位
        
        Args:
            level: 檔位等級 (0-7)
        """
        if not self.gpio_initialized:
            self.logger.warning("GPIO未初始化，無法控制氣泡盤")
            return
        
        # 限制檔位範圍
        level = max(0, min(7, level))
        self.airflow_level = level
        
        if GPIO_AVAILABLE:
            try:
                # 3-bit二進制控制
                for i, pin in enumerate(self.airflow_pins):
                    bit_value = (level >> i) & 1
                    GPIO.output(pin, GPIO.HIGH if bit_value else GPIO.LOW)
                
                self.logger.info(f"氣泡盤檔位設定: {level}")
                
            except Exception as e:
                self.logger.error(f"氣泡盤控制失敗: {e}")
        else:
            # 模擬模式
            self.logger.info(f"氣泡盤模擬檔位: {level}")
    
    def get_airflow_level(self) -> int:
        """
        獲取當前氣泡盤檔位
        
        Returns:
            當前檔位等級
        """
        return self.airflow_level
    
    def pulse_led(self, duration: float = 1.0):
        """
        LED脈衝閃爍
        
        Args:
            duration: 脈衝持續時間 (秒)
        """
        import time
        
        self.set_led_state(False)
        time.sleep(duration / 2)
        self.set_led_state(True)
        time.sleep(duration / 2)
    
    def test_all_outputs(self):
        """測試所有輸出"""
        import time
        
        self.logger.info("開始GPIO輸出測試...")
        
        # 測試LED
        self.logger.info("測試LED...")
        for i in range(3):
            self.set_led_state(True)
            time.sleep(0.5)
            self.set_led_state(False)
            time.sleep(0.5)
        self.set_led_state(True)  # 恢復開啟狀態
        
        # 測試氣泡盤所有檔位
        self.logger.info("測試氣泡盤...")
        for level in range(8):
            self.set_airflow_level(level)
            time.sleep(1.0)
        self.set_airflow_level(0)  # 恢復關閉狀態
        
        self.logger.info("GPIO測試完成")
    
    def cleanup(self):
        """清理GPIO資源"""
        if GPIO_AVAILABLE and self.gpio_initialized:
            try:
                # 關閉所有輸出
                GPIO.output(self.led_pin, GPIO.LOW)
                for pin in self.airflow_pins:
                    GPIO.output(pin, GPIO.LOW)
                
                # 清理GPIO
                GPIO.cleanup()
                self.logger.info("GPIO資源已清理")
                
            except Exception as e:
                self.logger.error(f"GPIO清理失敗: {e}")
        else:
            self.logger.info("GPIO模擬資源已清理")
        
        self.gpio_initialized = False
    
    def get_status(self) -> dict:
        """
        獲取GPIO狀態
        
        Returns:
            狀態字典
        """
        return {
            'gpio_available': GPIO_AVAILABLE,
            'gpio_initialized': self.gpio_initialized,
            'led_pin': self.led_pin,
            'airflow_pins': self.airflow_pins,
            'current_airflow_level': self.airflow_level,
            'led_brightness': self.led_brightness
        }
    
    def __del__(self):
        """析構函數"""
        self.cleanup()
