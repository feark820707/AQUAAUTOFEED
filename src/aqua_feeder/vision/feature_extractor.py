"""
特徵提取器
負責提取ME、RSI、POP、FLOW等特徵值
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from scipy import fftpack
from collections import deque

class FeatureExtractor:
    """特徵提取器"""
    
    def __init__(self, config: Dict):
        """
        初始化特徵提取器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 提取配置
        self.feature_config = config.get('feature_extraction', {})
        
        # 動態能量計算用的歷史幀
        temporal_window = self.feature_config.get('motion_energy', {}).get('temporal_window', 5)
        self.frame_buffer = deque(maxlen=temporal_window)
        
        # 光流計算器
        self.flow_params = dict(
            pyr_scale=0.5,
            levels=self.feature_config.get('optical_flow', {}).get('pyramid_levels', 3),
            winsize=self.feature_config.get('optical_flow', {}).get('window_size', 15),
            iterations=3,
            poly_n=5,
            poly_sigma=1.1,
            flags=0
        )
        
        # 前一幀（用於光流計算）
        self.prev_frame = None
        
        # 基線值
        fusion_config = config.get('feature_fusion', {})
        self.baseline = fusion_config.get('baseline', {})
        self.ME0 = self.baseline.get('ME0', 10.0)
        self.RSI0 = self.baseline.get('RSI0', 0.2)
        
    def extract_features(self, rois: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        從ROI中提取所有特徵
        
        Args:
            rois: ROI字典 {'roi_bub': array, 'roi_ring': array}
            
        Returns:
            特徵字典 {'ME': float, 'RSI': float, 'POP': float, 'FLOW': float}
        """
        features = {}
        
        # 動態能量 (Motion Energy)
        if 'roi_ring' in rois:
            features['ME'] = self._extract_motion_energy(rois['roi_ring'])
            features['ME_ring'] = features['ME']  # 環狀區域的動態能量
        else:
            features['ME'] = 0.0
            features['ME_ring'] = 0.0
        
        # 波紋頻譜指數 (Ripple Spectral Index)
        if 'roi_ring' in rois:
            features['RSI'] = self._extract_ripple_spectral_index(rois['roi_ring'])
        else:
            features['RSI'] = self.RSI0
        
        # 破泡事件率 (Bubble Pop Events)
        if 'roi_bub' in rois:
            features['POP'] = self._extract_bubble_pop_events(rois['roi_bub'])
        else:
            features['POP'] = 0.0
        
        # 光流不一致度 (Optical Flow Inconsistency)
        if 'roi_ring' in rois:
            features['FLOW'] = self._extract_optical_flow_inconsistency(rois['roi_ring'])
        else:
            features['FLOW'] = 0.0
        
        return features
    
    def _extract_motion_energy(self, roi: np.ndarray) -> float:
        """
        提取動態能量特徵
        
        Args:
            roi: 感興趣區域影像
            
        Returns:
            動態能量值
        """
        # 將當前幀加入緩衝區
        self.frame_buffer.append(roi.copy())
        
        if len(self.frame_buffer) < 2:
            return self.ME0
        
        # 計算相鄰幀差
        current_frame = self.frame_buffer[-1]
        prev_frame = self.frame_buffer[-2]
        
        # 幀差
        diff = cv2.absdiff(current_frame, prev_frame)
        
        # 閾值化
        threshold = self.feature_config.get('motion_energy', {}).get('threshold', 15)
        _, binary = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        # 計算動態像素比例
        motion_pixels = np.sum(binary > 0)
        total_pixels = binary.shape[0] * binary.shape[1]
        
        if total_pixels > 0:
            motion_energy = (motion_pixels / total_pixels) * 100.0
        else:
            motion_energy = 0.0
        
        return motion_energy
    
    def _extract_ripple_spectral_index(self, roi: np.ndarray) -> float:
        """
        提取波紋頻譜指數
        
        Args:
            roi: 感興趣區域影像
            
        Returns:
            RSI值
        """
        try:
            # 計算2D FFT
            f_transform = fftpack.fft2(roi.astype(np.float32))
            f_shift = fftpack.fftshift(f_transform)
            magnitude_spectrum = np.abs(f_shift)
            
            # 獲取頻域配置
            fft_config = self.feature_config.get('ripple_spectral', {})
            high_freq_start = fft_config.get('high_freq_start', 0.3)
            low_freq_end = fft_config.get('low_freq_end', 0.1)
            
            # 計算頻率座標
            rows, cols = roi.shape
            center_row, center_col = rows // 2, cols // 2
            
            # 創建頻率掩碼
            y, x = np.ogrid[:rows, :cols]
            distance = np.sqrt((x - center_col)**2 + (y - center_row)**2)
            max_distance = min(center_row, center_col)
            
            # 正規化距離 (0-1)
            normalized_distance = distance / max_distance
            
            # 高頻和低頻掩碼
            high_freq_mask = normalized_distance >= high_freq_start
            low_freq_mask = normalized_distance <= low_freq_end
            
            # 計算能量
            high_freq_energy = np.sum(magnitude_spectrum[high_freq_mask]**2)
            low_freq_energy = np.sum(magnitude_spectrum[low_freq_mask]**2)
            
            # 計算RSI
            if low_freq_energy > 0:
                rsi = high_freq_energy / low_freq_energy
            else:
                rsi = self.RSI0
            
            return float(rsi)
            
        except Exception as e:
            self.logger.warning(f"RSI計算失敗: {e}")
            return self.RSI0
    
    def _extract_bubble_pop_events(self, roi: np.ndarray) -> float:
        """
        提取破泡事件率
        
        Args:
            roi: 氣泡檢測區域影像
            
        Returns:
            POP值（每秒破泡事件數）
        """
        try:
            # 高斯模糊
            blurred = cv2.GaussianBlur(roi, (5, 5), 0)
            
            # 自適應閾值
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 形態學運算
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # 尋找輪廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 篩選氣泡輪廓
            bubble_config = self.feature_config.get('bubble_pop', {})
            min_area = bubble_config.get('min_area', 50)
            max_area = bubble_config.get('max_area', 500)
            circularity_threshold = bubble_config.get('circularity_threshold', 0.7)
            
            bubble_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area <= area <= max_area:
                    # 檢查圓形度
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        if circularity >= circularity_threshold:
                            bubble_count += 1
            
            # 假設30fps，估算每秒破泡數
            pop_rate = bubble_count * 30.0 / 1000.0  # 簡化計算
            
            return float(pop_rate)
            
        except Exception as e:
            self.logger.warning(f"POP計算失敗: {e}")
            return 0.0
    
    def _extract_optical_flow_inconsistency(self, roi: np.ndarray) -> float:
        """
        提取光流不一致度
        
        Args:
            roi: 感興趣區域影像
            
        Returns:
            FLOW值
        """
        try:
            if self.prev_frame is None:
                self.prev_frame = roi.copy()
                return 0.0
            
            # 計算光流
            flow = cv2.calcOpticalFlowPyrLK(
                self.prev_frame, roi, None, None, **self.flow_params
            )
            
            if flow[0] is not None:
                # 計算光流向量的標準差
                flow_vectors = flow[0]
                if len(flow_vectors) > 0:
                    # 計算速度大小
                    flow_magnitude = np.sqrt(flow_vectors[:, :, 0]**2 + flow_vectors[:, :, 1]**2)
                    
                    # 計算不一致度（標準差）
                    flow_inconsistency = np.std(flow_magnitude)
                else:
                    flow_inconsistency = 0.0
            else:
                flow_inconsistency = 0.0
            
            # 更新前一幀
            self.prev_frame = roi.copy()
            
            return float(flow_inconsistency)
            
        except Exception as e:
            self.logger.warning(f"FLOW計算失敗: {e}")
            return 0.0
    
    def reset_buffers(self):
        """重置緩衝區"""
        self.frame_buffer.clear()
        self.prev_frame = None
        self.logger.info("特徵提取器緩衝區已重置")
    
    def get_baseline_values(self) -> Dict[str, float]:
        """獲取基線值"""
        return {
            'ME0': self.ME0,
            'RSI0': self.RSI0
        }
