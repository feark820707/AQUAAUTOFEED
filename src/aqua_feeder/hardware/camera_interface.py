"""
相機接口
負責相機的初始化、影像擷取和參數控制
"""

import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Tuple
from queue import Queue

class CameraInterface:
    """相機接口類"""
    
    def __init__(self, config: dict):
        """
        初始化相機接口
        
        Args:
            config: 相機配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 相機參數
        camera_config = config.get('camera', {})
        self.device_id = camera_config.get('device_id', 0)
        self.resolution = camera_config.get('resolution', [1920, 1080])
        self.target_fps = camera_config.get('fps', 60)
        
        # 相機對象
        self.cap = None
        self.is_opened = False
        
        # 執行緒相關
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.frame_queue = Queue(maxsize=10)
        
        # 統計信息
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        
        # 初始化相機
        self._initialize_camera()
    
    def _initialize_camera(self):
        """
        初始化相機設備
        符合需求書：單鏡頭攝影模組 1080p/60fps，具備俯視拍攝能力
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                self.logger.error(f"無法開啟相機設備 {self.device_id}")
                return
            
            # 設定解析度 - 支援1080p
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            # 設定幀率 - 目標60fps
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # 設定緩衝區大小
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 設定自動曝光（根據需求書的exposure_mode）
            exposure_mode = self.config.get('camera', {}).get('exposure_mode', 'auto')
            if exposure_mode == 'auto':
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            
            # 驗證設定
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"相機初始化成功:")
            self.logger.info(f"  解析度: {actual_width}x{actual_height}")
            self.logger.info(f"  目標FPS: {actual_fps}")
            self.logger.info(f"  設備ID: {self.device_id}")
            
            self.is_opened = True
            
        except Exception as e:
            self.logger.error(f"相機初始化失敗: {e}")
            self.is_opened = False
    
    def start_capture(self):
        """
        開始影像擷取執行緒
        確保達到需求書要求的60fps性能
        """
        if not self.is_opened:
            self.logger.error("相機未正確初始化")
            return False
            
        if self.capture_thread is not None and self.capture_thread.is_alive():
            self.logger.warning("擷取執行緒已在運行")
            return True
            
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        self.logger.info("相機擷取執行緒已啟動")
        return True
    
    def _capture_loop(self):
        """
        相機擷取主迴圈
        實現高性能影像擷取，滿足即時性要求
        """
        frame_time = 1.0 / self.target_fps
        last_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    self.logger.error("無法讀取相機幀")
                    break
                
                current_time = time.time()
                
                # 將幀加入佇列（非阻塞）
                if not self.frame_queue.full():
                    self.frame_queue.put((frame.copy(), current_time))
                else:
                    # 佇列滿時丟棄最舊的幀
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put((frame.copy(), current_time))
                    except:
                        pass
                
                # 更新統計
                self.frame_count += 1
                if current_time - self.last_fps_time >= 1.0:
                    self.current_fps = self.frame_count / (current_time - self.last_fps_time)
                    self.frame_count = 0
                    self.last_fps_time = current_time
                
                # 控制幀率
                elapsed = current_time - last_time
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                last_time = current_time
                
            except Exception as e:
                self.logger.error(f"擷取迴圈錯誤: {e}")
                break
    
    def get_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """
        獲取最新影像幀
        
        Returns:
            Tuple[影像幀, 時間戳] 或 None
        """
        try:
            if not self.frame_queue.empty():
                return self.frame_queue.get_nowait()
        except:
            pass
        return None
    
    def stop_capture(self):
        """停止影像擷取"""
        if self.capture_thread is not None:
            self.stop_event.set()
            self.capture_thread.join(timeout=2.0)
            self.capture_thread = None
        
        self.logger.info("相機擷取已停止")
    
    def release(self):
        """釋放相機資源"""
        self.stop_capture()
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_opened = False
        self.logger.info("相機資源已釋放")
    
    def get_fps(self) -> float:
        """
        獲取當前實際FPS
        用於異常檢測模塊監控性能
        """
        return self.current_fps
    
    def is_camera_connected(self) -> bool:
        """
        檢查相機連接狀態
        支援異常檢測模塊的相機斷線檢測
        """
        if not self.is_opened or self.cap is None:
            return False
        
        # 嘗試讀取一幀來檢測連接
        try:
            ret, _ = self.cap.read()
            return ret
        except:
            return False
    
    def get_camera_info(self) -> dict:
        """
        獲取相機信息
        用於系統監控和日誌記錄
        """
        if not self.is_opened:
            return {}
        
        return {
            'device_id': self.device_id,
            'resolution': self.resolution,
            'target_fps': self.target_fps,
            'current_fps': self.current_fps,
            'is_connected': self.is_camera_connected(),
            'frame_count': self.frame_count
        }
    
    def adjust_exposure(self, mode: str = 'auto', value: Optional[float] = None):
        """
        調整曝光設定
        支援不同光照條件下的影像品質優化
        
        Args:
            mode: 'auto' 或 'manual'
            value: 手動模式下的曝光值
        """
        if not self.is_opened:
            return
        
        try:
            if mode == 'auto':
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                self.logger.info("設定為自動曝光模式")
            elif mode == 'manual' and value is not None:
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                self.cap.set(cv2.CAP_PROP_EXPOSURE, value)
                self.logger.info(f"設定為手動曝光模式，值: {value}")
        except Exception as e:
            self.logger.error(f"曝光調整失敗: {e}")
    
    def set_focus(self, focus_value: Optional[float] = None):
        """
        設定對焦
        優化俯視拍攝的影像清晰度
        
        Args:
            focus_value: 對焦值，None為自動對焦
        """
        if not self.is_opened:
            return
        
        try:
            if focus_value is None:
                # 自動對焦
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                self.logger.info("設定為自動對焦")
            else:
                # 手動對焦
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                self.cap.set(cv2.CAP_PROP_FOCUS, focus_value)
                self.logger.info(f"設定手動對焦值: {focus_value}")
        except Exception as e:
            self.logger.error(f"對焦設定失敗: {e}")
    
    def __del__(self):
        """析構函數"""
        self.release()
        """初始化相機"""
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                raise Exception(f"無法開啟相機設備 {self.device_id}")
            
            # 設定相機參數
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # 驗證設定
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"相機初始化成功:")
            self.logger.info(f"  解析度: {actual_width}x{actual_height} (目標: {self.resolution[0]}x{self.resolution[1]})")
            self.logger.info(f"  幀率: {actual_fps:.1f} (目標: {self.target_fps})")
            
            self.is_opened = True
            
        except Exception as e:
            self.logger.error(f"相機初始化失敗: {e}")
            self.is_opened = False
    
    def start_capture(self):
        """啟動影像擷取執行緒"""
        if not self.is_opened:
            self.logger.error("相機未初始化，無法啟動擷取")
            return False
        
        if self.capture_thread is not None and self.capture_thread.is_alive():
            self.logger.warning("擷取執行緒已在運行")
            return True
        
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.logger.info("影像擷取執行緒已啟動")
        return True
    
    def stop_capture(self):
        """停止影像擷取執行緒"""
        if self.capture_thread is not None:
            self.stop_event.set()
            self.capture_thread.join(timeout=2.0)
            
            if self.capture_thread.is_alive():
                self.logger.warning("擷取執行緒未能正常停止")
            else:
                self.logger.info("影像擷取執行緒已停止")
    
    def _capture_loop(self):
        """影像擷取迴圈"""
        self.logger.info("擷取迴圈啟動")
        
        while not self.stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    self.logger.warning("無法讀取影像幀")
                    time.sleep(0.01)
                    continue
                
                # 更新FPS統計
                self._update_fps_stats()
                
                # 將幀加入佇列
                if not self.frame_queue.full():
                    self.frame_queue.put((frame.copy(), time.time()))
                else:
                    # 佇列滿時丟棄最舊的幀
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put((frame.copy(), time.time()))
                    except:
                        pass
                
            except Exception as e:
                self.logger.error(f"擷取迴圈錯誤: {e}")
                time.sleep(0.1)
        
        self.logger.info("擷取迴圈結束")
    
    def get_frame(self, timeout: float = 1.0) -> Optional[Tuple[np.ndarray, float]]:
        """
        獲取最新的影像幀
        
        Args:
            timeout: 超時時間 (秒)
            
        Returns:
            Tuple[影像幀, 時間戳] 或 None
        """
        try:
            if self.frame_queue.empty():
                return None
                
            frame, timestamp = self.frame_queue.get(timeout=timeout)
            return frame, timestamp
            
        except Exception as e:
            self.logger.debug(f"獲取幀失敗: {e}")
            return None
    
    def _update_fps_stats(self):
        """更新FPS統計"""
        self.frame_count += 1
        current_time = time.time()
        
        # 每秒計算一次FPS
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def get_fps(self) -> float:
        """獲取當前FPS"""
        return self.current_fps
    
    def set_exposure(self, exposure: int):
        """
        設定曝光值
        
        Args:
            exposure: 曝光值
        """
        if self.cap is not None:
            try:
                self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
                self.logger.info(f"曝光值設定為: {exposure}")
            except Exception as e:
                self.logger.error(f"設定曝光值失敗: {e}")
    
    def set_gain(self, gain: float):
        """
        設定增益
        
        Args:
            gain: 增益值
        """
        if self.cap is not None:
            try:
                self.cap.set(cv2.CAP_PROP_GAIN, gain)
                self.logger.info(f"增益值設定為: {gain}")
            except Exception as e:
                self.logger.error(f"設定增益值失敗: {e}")
    
    def get_camera_info(self) -> dict:
        """
        獲取相機信息
        
        Returns:
            相機信息字典
        """
        if not self.is_opened:
            return {'error': '相機未開啟'}
        
        try:
            info = {
                'device_id': self.device_id,
                'resolution': [
                    int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                ],
                'fps': self.cap.get(cv2.CAP_PROP_FPS),
                'current_fps': self.current_fps,
                'exposure': self.cap.get(cv2.CAP_PROP_EXPOSURE),
                'gain': self.cap.get(cv2.CAP_PROP_GAIN),
                'brightness': self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
                'contrast': self.cap.get(cv2.CAP_PROP_CONTRAST),
                'is_capturing': self.capture_thread is not None and self.capture_thread.is_alive()
            }
            return info
        except Exception as e:
            self.logger.error(f"獲取相機信息失敗: {e}")
            return {'error': str(e)}
    
    def release(self):
        """釋放相機資源"""
        self.stop_capture()
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        self.is_opened = False
        self.logger.info("相機資源已釋放")
    
    def __del__(self):
        """析構函數"""
        self.release()
