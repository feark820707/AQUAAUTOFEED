"""
影像處理器
負責影像前處理：CLAHE、直方圖匹配、ROI切割等
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional
import logging

class ImageProcessor:
    """影像前處理器"""
    
    def __init__(self, config: Dict):
        """
        初始化影像處理器
        
        Args:
            config: 配置字典，包含CLAHE、ROI等參數
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化CLAHE
        clahe_config = config.get('preprocessing', {}).get('clahe', {})
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_config.get('clip_limit', 2.0),
            tileGridSize=tuple(clahe_config.get('tile_grid_size', [8, 8]))
        )
        
        # ROI配置
        self.roi_config = config.get('roi_config', {})
        
        # 直方圖匹配參考圖像
        self.reference_hist = None
        hist_config = config.get('preprocessing', {}).get('histogram_matching', {})
        if hist_config.get('enable', False):
            ref_path = hist_config.get('reference_image_path')
            if ref_path:
                self._load_reference_histogram(ref_path)
    
    def _load_reference_histogram(self, image_path: str):
        """載入參考圖像的直方圖"""
        try:
            ref_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if ref_img is not None:
                self.reference_hist = cv2.calcHist([ref_img], [0], None, [256], [0, 256])
                self.logger.info(f"載入參考直方圖: {image_path}")
            else:
                self.logger.warning(f"無法載入參考圖像: {image_path}")
        except Exception as e:
            self.logger.error(f"載入參考直方圖失敗: {e}")
    
    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        對輸入影像進行前處理
        
        Args:
            image: 輸入RGB影像
            
        Returns:
            Tuple[處理後的灰度影像, ROI字典]
        """
        # 轉換為灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # CLAHE增強
        enhanced = self.clahe.apply(gray)
        
        # 直方圖匹配（如果啟用）
        if self.reference_hist is not None:
            enhanced = self._histogram_matching(enhanced)
        
        # 提取ROI區域
        rois = self._extract_rois(enhanced)
        
        return enhanced, rois
    
    def _histogram_matching(self, image: np.ndarray) -> np.ndarray:
        """
        直方圖匹配到參考圖像
        
        Args:
            image: 輸入灰度影像
            
        Returns:
            匹配後的影像
        """
        # 計算輸入影像直方圖
        input_hist = cv2.calcHist([image], [0], None, [256], [0, 256])
        
        # 計算累積分布函數
        input_cdf = np.cumsum(input_hist)
        input_cdf = input_cdf / input_cdf[-1]  # 正規化
        
        ref_cdf = np.cumsum(self.reference_hist)
        ref_cdf = ref_cdf / ref_cdf[-1]  # 正規化
        
        # 建立查找表
        lut = np.zeros(256, dtype=np.uint8)
        for i in range(256):
            # 找到最接近的參考CDF值
            diff = np.abs(ref_cdf - input_cdf[i])
            lut[i] = np.argmin(diff)
        
        # 應用查找表
        matched = cv2.LUT(image, lut)
        return matched
    
    def _extract_rois(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        提取感興趣區域
        
        Args:
            image: 處理後的灰度影像
            
        Returns:
            ROI字典 {'roi_bub': array, 'roi_ring': array}
        """
        rois = {}
        
        # 提取氣泡檢測區域
        if 'roi_bub' in self.roi_config:
            bub_cfg = self.roi_config['roi_bub']
            x, y = bub_cfg['x'], bub_cfg['y']
            w, h = bub_cfg['width'], bub_cfg['height']
            
            # 確保ROI在影像範圍內
            x = max(0, min(x, image.shape[1] - w))
            y = max(0, min(y, image.shape[0] - h))
            
            rois['roi_bub'] = image[y:y+h, x:x+w]
        
        # 提取環狀波紋檢測區域
        if 'roi_ring' in self.roi_config:
            ring_cfg = self.roi_config['roi_ring']
            x, y = ring_cfg['x'], ring_cfg['y']
            w, h = ring_cfg['width'], ring_cfg['height']
            
            # 確保ROI在影像範圍內
            x = max(0, min(x, image.shape[1] - w))
            y = max(0, min(y, image.shape[0] - h))
            
            rois['roi_ring'] = image[y:y+h, x:x+w]
        
        return rois
    
    def get_roi_coordinates(self, roi_name: str) -> Optional[Tuple[int, int, int, int]]:
        """
        獲取ROI座標
        
        Args:
            roi_name: ROI名稱 ('roi_bub' 或 'roi_ring')
            
        Returns:
            (x, y, width, height) 或 None
        """
        if roi_name in self.roi_config:
            cfg = self.roi_config[roi_name]
            return (cfg['x'], cfg['y'], cfg['width'], cfg['height'])
        return None
    
    def update_roi(self, roi_name: str, x: int, y: int, width: int, height: int):
        """
        更新ROI區域
        
        Args:
            roi_name: ROI名稱
            x, y: 左上角座標
            width, height: 寬高
        """
        if roi_name not in self.roi_config:
            self.roi_config[roi_name] = {}
        
        self.roi_config[roi_name].update({
            'x': x,
            'y': y, 
            'width': width,
            'height': height
        })
        
        self.logger.info(f"更新ROI {roi_name}: ({x},{y}) {width}x{height}")
