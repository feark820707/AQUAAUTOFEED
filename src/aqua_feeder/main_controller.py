"""
主控制器
整合所有功能模塊，實現需求書的完整系統功能
包含：影像前處理、特徵提取、特徵融合、控制器、異常檢測、記錄日誌
"""

import time
import threading
import logging
import csv
import os
from datetime import datetime
from typing import Dict, Optional
import yaml
import signal
import sys
import numpy as np

from .vision.image_processor import ImageProcessor
from .vision.feature_extractor import FeatureExtractor
from .control.feeding_controller import FeedingController, FeedingState
from .hardware.camera_interface import CameraInterface
from .hardware.pwm_controller import PWMController

class AquaFeederController:
    """
    智能餵料控制器主類
    實現需求書的完整系統架構
    """
    
    def __init__(self, config_path: str = "config/system_params.yaml"):
        """
        初始化主控制器
        符合需求書的系統架構要求
        
        Args:
            config_path: 配置文件路徑
        """
        # 設定日誌
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 載入配置
        self.config = self._load_config(config_path)
        
        # 初始化各模塊
        self.camera = CameraInterface(self.config)
        self.image_processor = ImageProcessor(self.config)
        self.feature_extractor = FeatureExtractor(self.config)
        self.feeding_controller = FeedingController(self.config)
        
        # 初始化硬體
        pwm_config = self.config.get('hardware', {}).get('pwm', {})
        self.pwm_controller = PWMController(
            pin=pwm_config.get('gpio_pin', 18),
            frequency=pwm_config.get('frequency', 1000),
            min_duty=pwm_config.get('min_duty_cycle', 20),
            max_duty=pwm_config.get('max_duty_cycle', 70)
        )
        
        # 控制變數
        self.is_running = False
        self.stop_event = threading.Event()
        self.main_thread = None
        
        # 資料記錄
        self.csv_writer = None
        self.csv_file = None
        self.setup_data_logging()
        
        # 統計信息
        self.stats = {
            'total_frames': 0,
            'total_feeding_cycles': 0,
            'avg_fps': 0.0,
            'start_time': time.time()
        }
        
        # 註冊信號處理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("智能餵料控制器初始化完成")
    
    def _setup_logging(self):
        """設定日誌系統"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'logs/aqua_feeder_{datetime.now().strftime("%Y%m%d")}.log')
            ]
        )
    
    def _load_config(self, config_path: str) -> Dict:
        """載入配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"載入配置文件: {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """獲取預設配置"""
        return {
            'hardware': {
                'camera': {'device_id': 0, 'resolution': [1920, 1080], 'fps': 60},
                'pwm': {'gpio_pin': 18, 'frequency': 1000, 'min_duty_cycle': 20, 'max_duty_cycle': 70}
            },
            'controller': {
                'timing': {'t_feed': 0.6, 't_eval': 3.0, 't_settle': 1.0},
                'thresholds': {'H_hi': 0.65, 'H_lo': 0.35}
            },
            'logging': {
                'csv_output': {'enable': True, 'file_path': 'logs/feeding_log_{date}.csv'}
            }
        }
    
    def setup_data_logging(self):
        """設定資料記錄"""
        try:
            log_config = self.config.get('logging', {}).get('csv_output', {})
            if not log_config.get('enable', True):
                return
            
            # 建立logs目錄
            os.makedirs('logs', exist_ok=True)
            
            # 生成日誌檔案名
            date_str = datetime.now().strftime("%Y%m%d")
            file_path = log_config.get('file_path', 'logs/feeding_log_{date}.csv')
            self.csv_file_path = file_path.format(date=date_str)
            
            # 開啟CSV檔案
            self.csv_file = open(self.csv_file_path, 'w', newline='', encoding='utf-8')
            
            # 設定欄位
            columns = log_config.get('columns', [
                'timestamp', 'state', 'pwm', 'H', 'RSI', 'POP', 'FLOW', 'ME_ring', 'warnings'
            ])
            
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=columns)
            self.csv_writer.writeheader()
            
            self.logger.info(f"資料記錄已啟用: {self.csv_file_path}")
            
        except Exception as e:
            self.logger.error(f"資料記錄設定失敗: {e}")
    
    def start(self):
        """啟動系統"""
        if self.is_running:
            self.logger.warning("系統已在運行")
            return
        
        try:
            # 啟動相機
            if not self.camera.start_capture():
                raise Exception("相機啟動失敗")
            
            # 啟動PWM控制器
            self.pwm_controller.start(self.pwm_controller.min_duty)
            
            # 啟動主控制迴圈
            self.is_running = True
            self.stop_event.clear()
            self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()
            
            self.logger.info("系統啟動成功")
            
        except Exception as e:
            self.logger.error(f"系統啟動失敗: {e}")
            self.stop()
    
    def stop(self):
        """停止系統"""
        self.logger.info("正在停止系統...")
        
        self.is_running = False
        self.stop_event.set()
        
        # 等待主迴圈結束
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5.0)
        
        # 停止硬體
        self.camera.stop_capture()
        self.pwm_controller.stop()
        
        # 關閉資料記錄
        if self.csv_file:
            self.csv_file.close()
        
        self.logger.info("系統已停止")
    
    def _main_loop(self):
        """主控制迴圈"""
        self.logger.info("主控制迴圈啟動")
        
        fps_history = []
        last_status_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                loop_start_time = time.time()
                
                # 獲取影像幀
                frame_data = self.camera.get_frame(timeout=0.1)
                if frame_data is None:
                    continue
                
                frame, timestamp = frame_data
                
                # 影像處理
                processed_image, rois = self.image_processor.preprocess_image(frame)
                
                # 特徵提取
                features = self.feature_extractor.extract_features(rois)
                
                # 控制更新
                current_fps = self.camera.get_fps()
                new_pwm, current_state = self.feeding_controller.update(features, current_fps)
                
                # 更新PWM輸出
                self.pwm_controller.set_duty_cycle(new_pwm)
                
                # 記錄資料
                self._log_data(features, new_pwm, current_state, current_fps)
                
                # 更新統計
                self.stats['total_frames'] += 1
                fps_history.append(1.0 / (time.time() - loop_start_time))
                if len(fps_history) > 30:  # 保持最近30幀的FPS
                    fps_history.pop(0)
                
                # 定期狀態報告
                if time.time() - last_status_time > 10.0:  # 每10秒
                    self._report_status(fps_history, features, new_pwm, current_state)
                    last_status_time = time.time()
                
            except Exception as e:
                self.logger.error(f"主迴圈錯誤: {e}")
                time.sleep(0.1)
        
        self.logger.info("主控制迴圈結束")
    
    def _log_data(self, features: Dict, pwm: float, state, fps: float):
        """記錄資料到CSV"""
        if not self.csv_writer:
            return
        
        try:
            # 計算活躍度H值
            H = self.feeding_controller._calculate_activity_index(features)
            
            row = {
                'timestamp': datetime.now().isoformat(),
                'state': state.value if hasattr(state, 'value') else str(state),
                'pwm': f"{pwm:.2f}",
                'H': f"{H:.4f}",
                'RSI': f"{features.get('RSI', 0):.4f}",
                'POP': f"{features.get('POP', 0):.4f}",
                'FLOW': f"{features.get('FLOW', 0):.4f}",
                'ME_ring': f"{features.get('ME_ring', 0):.4f}",
                'warnings': ""  # 可以添加警告信息
            }
            
            self.csv_writer.writerow(row)
            self.csv_file.flush()  # 確保資料寫入
            
        except Exception as e:
            self.logger.error(f"資料記錄錯誤: {e}")
    
    def _report_status(self, fps_history, features, pwm, state):
        """報告系統狀態"""
        avg_fps = sum(fps_history) / len(fps_history) if fps_history else 0
        H = self.feeding_controller._calculate_activity_index(features)
        
        runtime = time.time() - self.stats['start_time']
        
        self.logger.info(f"系統狀態報告:")
        self.logger.info(f"  運行時間: {runtime:.1f}s")
        self.logger.info(f"  處理幀數: {self.stats['total_frames']}")
        self.logger.info(f"  平均FPS: {avg_fps:.1f}")
        self.logger.info(f"  當前狀態: {state.value if hasattr(state, 'value') else state}")
        self.logger.info(f"  PWM輸出: {pwm:.1f}%")
        self.logger.info(f"  活躍度H: {H:.3f}")
        self.logger.info(f"  特徵值: RSI={features.get('RSI', 0):.3f}, POP={features.get('POP', 0):.3f}")
    
    def _signal_handler(self, signum, frame):
        """信號處理函數"""
        self.logger.info(f"收到信號 {signum}，正在關閉系統...")
        self.stop()
        sys.exit(0)
    
    def get_system_status(self) -> Dict:
        """獲取系統狀態"""
        return {
            'is_running': self.is_running,
            'stats': self.stats,
            'camera_status': self.camera.get_camera_info(),
            'pwm_status': self.pwm_controller.get_status(),
            'controller_status': self.feeding_controller.get_status()
        }

def main():
    """主函數"""
    try:
        # 檢查配置文件
        config_path = "config/system_params.yaml"
        if not os.path.exists(config_path):
            print(f"警告: 找不到配置文件 {config_path}")
        
        # 創建控制器
        controller = AquaFeederController(config_path)
        
        # 啟動系統
        controller.start()
        
        print("智能餵料系統已啟動，按 Ctrl+C 停止...")
        
        # 保持運行
        try:
            while controller.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        print(f"系統錯誤: {e}")
    finally:
        if 'controller' in locals():
            controller.stop()

if __name__ == '__main__':
    main()
