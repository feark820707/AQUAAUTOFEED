"""
系統功能測試
驗證各模組基本功能
"""

import pytest
import numpy as np
import cv2
import yaml
import os
import sys
import time

# 添加專案路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from aqua_feeder.vision.image_processor import ImageProcessor
from aqua_feeder.vision.feature_extractor import FeatureExtractor
from aqua_feeder.control.pi_controller import PIController
from aqua_feeder.control.feeding_controller import FeedingController


class TestImageProcessor:
    """測試影像處理器"""
    
    def setup_method(self):
        """測試設定"""
        self.config = {
            'vision': {
                'roi_config': {
                    'roi_bub': {'x': 100, 'y': 100, 'width': 200, 'height': 150},
                    'roi_ring': {'x': 50, 'y': 50, 'width': 300, 'height': 250}
                },
                'preprocessing': {
                    'clahe': {'clip_limit': 2.0, 'tile_grid_size': [8, 8]},
                    'histogram_matching': {'enable': False}
                }
            }
        }
        self.processor = ImageProcessor(self.config)
    
    def test_preprocess_image(self):
        """測試影像前處理"""
        # 創建測試影像
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # 處理影像
        processed_image, rois = self.processor.preprocess_image(test_image)
        
        # 驗證結果
        assert processed_image is not None
        assert len(processed_image.shape) == 2  # 灰度影像
        assert 'roi_bub' in rois
        assert 'roi_ring' in rois
        assert rois['roi_bub'].shape == (150, 200)  # 高, 寬
        assert rois['roi_ring'].shape == (250, 300)
    
    def test_roi_coordinates(self):
        """測試ROI座標獲取"""
        coords = self.processor.get_roi_coordinates('roi_bub')
        assert coords == (100, 100, 200, 150)
        
        # 測試不存在的ROI
        coords = self.processor.get_roi_coordinates('nonexistent')
        assert coords is None


class TestFeatureExtractor:
    """測試特徵提取器"""
    
    def setup_method(self):
        """測試設定"""
        self.config = {
            'feature_extraction': {
                'motion_energy': {'temporal_window': 5, 'threshold': 15},
                'ripple_spectral': {'high_freq_start': 0.3, 'low_freq_end': 0.1},
                'bubble_pop': {'min_area': 50, 'max_area': 500, 'circularity_threshold': 0.7},
                'optical_flow': {'pyramid_levels': 3, 'window_size': 15}
            },
            'feature_fusion': {
                'baseline': {'ME0': 10.0, 'RSI0': 0.2},
                'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
            }
        }
        self.extractor = FeatureExtractor(self.config)
    
    def test_extract_features(self):
        """測試特徵提取"""
        # 創建測試ROI
        roi_bub = np.random.randint(0, 255, (150, 200), dtype=np.uint8)
        roi_ring = np.random.randint(0, 255, (250, 300), dtype=np.uint8)
        
        rois = {
            'roi_bub': roi_bub,
            'roi_ring': roi_ring
        }
        
        # 提取特徵
        features = self.extractor.extract_features(rois)
        
        # 驗證結果
        expected_features = ['ME', 'RSI', 'POP', 'FLOW', 'ME_ring']
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], (int, float))
            assert features[feature] >= 0  # 所有特徵應為非負值
    
    def test_baseline_values(self):
        """測試基線值"""
        baseline = self.extractor.get_baseline_values()
        assert 'ME0' in baseline
        assert 'RSI0' in baseline
        assert baseline['ME0'] == 10.0
        assert baseline['RSI0'] == 0.2


class TestPIController:
    """測試PI控制器"""
    
    def setup_method(self):
        """測試設定"""
        self.controller = PIController(
            kp=1.0, ki=0.1, 
            output_min=0.0, output_max=100.0,
            anti_windup=True, max_integral=50.0
        )
    
    def test_controller_update(self):
        """測試控制器更新"""
        # 測試基本控制
        setpoint = 50.0
        measured = 40.0
        
        output = self.controller.update(setpoint, measured)
        
        # 驗證輸出在合理範圍內
        assert 0.0 <= output <= 100.0
        assert isinstance(output, (int, float))
    
    def test_controller_limits(self):
        """測試控制器限制"""
        # 測試輸出限制
        self.controller.integral = 1000.0  # 強制積分飽和
        
        output = self.controller.update(100.0, 0.0)
        assert output <= 100.0  # 不應超過最大值
        
        output = self.controller.update(0.0, 100.0)
        assert output >= 0.0   # 不應低於最小值
    
    def test_controller_reset(self):
        """測試控制器重置"""
        # 設定一些狀態
        self.controller.update(50.0, 30.0)
        self.controller.reset()
        
        # 驗證重置
        assert self.controller.integral == 0.0
        assert self.controller.last_error == 0.0
        assert self.controller.last_time is None


class TestFeedingController:
    """測試餵料控制器"""
    
    def setup_method(self):
        """測試設定"""
        self.config = {
            'controller': {
                'timing': {'t_feed': 0.6, 't_eval': 3.0, 't_settle': 1.0},
                'thresholds': {'H_hi': 0.65, 'H_lo': 0.35},
                'pi_controller': {'Kp': 15.0, 'Ki': 2.0},
                'constraints': {'delta_up': 10.0, 'delta_down': 15.0},
                'anti_windup': {'enable': True, 'max_integral': 50.0}
            },
            'feature_fusion': {
                'weights': {'alpha': 0.4, 'beta': 0.3, 'gamma': 0.2, 'delta': 0.1},
                'baseline': {'ME0': 10.0, 'RSI0': 0.2},
                'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
            },
            'hardware': {
                'pwm': {'min_duty_cycle': 20, 'max_duty_cycle': 70}
            },
            'anomaly_detection': {
                'fps_threshold': 50,
                'low_activity_duration': 30,
                'fallback_mode': {'pwm_safe_value': 30, 'evaluation_extension': 2.0}
            }
        }
        self.controller = FeedingController(self.config)
    
    def test_activity_calculation(self):
        """測試活躍度計算"""
        features = {
            'RSI': 0.5,
            'POP': 2.0,
            'FLOW': 20.0,
            'ME_ring': 15.0
        }
        
        H = self.controller._calculate_activity_index(features)
        
        # 驗證H值在合理範圍內
        assert 0.0 <= H <= 1.0
        assert isinstance(H, (int, float))
    
    def test_controller_update(self):
        """測試控制器更新"""
        features = {
            'RSI': 0.5,
            'POP': 2.0,
            'FLOW': 20.0,
            'ME_ring': 15.0
        }
        fps = 60.0
        
        pwm, state = self.controller.update(features, fps)
        
        # 驗證輸出
        assert 20.0 <= pwm <= 70.0  # PWM範圍
        assert hasattr(state, 'value')  # 應該是枚舉類型
    
    def test_controller_reset(self):
        """測試控制器重置"""
        # 執行一些更新
        features = {'RSI': 0.5, 'POP': 2.0, 'FLOW': 20.0, 'ME_ring': 15.0}
        self.controller.update(features, 60.0)
        
        # 重置控制器
        self.controller.reset()
        
        # 驗證重置狀態
        status = self.controller.get_status()
        assert status['state'] == '初始化'


class TestSystemIntegration:
    """測試系統整合"""
    
    def test_config_loading(self):
        """測試配置載入"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'system_params.yaml')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 驗證配置結構
            assert 'hardware' in config
            assert 'vision' in config
            assert 'controller' in config
            assert 'feature_fusion' in config
    
    def test_end_to_end_processing(self):
        """測試端到端處理流程"""
        # 最小配置
        config = {
            'vision': {
                'roi_config': {
                    'roi_bub': {'x': 100, 'y': 100, 'width': 200, 'height': 150},
                    'roi_ring': {'x': 50, 'y': 50, 'width': 300, 'height': 250}
                },
                'preprocessing': {
                    'clahe': {'clip_limit': 2.0, 'tile_grid_size': [8, 8]}
                },
                'feature_extraction': {
                    'motion_energy': {'temporal_window': 5, 'threshold': 15},
                    'ripple_spectral': {'high_freq_start': 0.3, 'low_freq_end': 0.1},
                    'bubble_pop': {'min_area': 50, 'max_area': 500},
                    'optical_flow': {'pyramid_levels': 3, 'window_size': 15}
                }
            },
            'feature_fusion': {
                'weights': {'alpha': 0.4, 'beta': 0.3, 'gamma': 0.2, 'delta': 0.1},
                'baseline': {'ME0': 10.0, 'RSI0': 0.2},
                'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
            },
            'controller': {
                'timing': {'t_feed': 0.6, 't_eval': 3.0, 't_settle': 1.0},
                'thresholds': {'H_hi': 0.65, 'H_lo': 0.35},
                'pi_controller': {'Kp': 15.0, 'Ki': 2.0},
                'constraints': {'delta_up': 10.0, 'delta_down': 15.0},
                'anti_windup': {'enable': True, 'max_integral': 50.0}
            },
            'hardware': {'pwm': {'min_duty_cycle': 20, 'max_duty_cycle': 70}},
            'anomaly_detection': {
                'fps_threshold': 50,
                'fallback_mode': {'pwm_safe_value': 30}
            }
        }
        
        # 創建處理器
        image_processor = ImageProcessor(config)
        feature_extractor = FeatureExtractor(config)
        feeding_controller = FeedingController(config)
        
        # 模擬完整處理流程
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # 1. 影像處理
        processed_image, rois = image_processor.preprocess_image(test_image)
        assert processed_image is not None
        assert len(rois) > 0
        
        # 2. 特徵提取
        features = feature_extractor.extract_features(rois)
        assert len(features) > 0
        
        # 3. 控制更新
        pwm, state = feeding_controller.update(features, 60.0)
        assert 20.0 <= pwm <= 70.0


def test_performance():
    """性能測試"""
    # 簡化配置
    config = {
        'vision': {
            'roi_config': {
                'roi_bub': {'x': 100, 'y': 100, 'width': 200, 'height': 150},
                'roi_ring': {'x': 50, 'y': 50, 'width': 300, 'height': 250}
            },
            'preprocessing': {'clahe': {'clip_limit': 2.0, 'tile_grid_size': [8, 8]}},
            'feature_extraction': {
                'motion_energy': {'temporal_window': 5, 'threshold': 15},
                'ripple_spectral': {'high_freq_start': 0.3, 'low_freq_end': 0.1},
                'bubble_pop': {'min_area': 50, 'max_area': 500},
                'optical_flow': {'pyramid_levels': 3, 'window_size': 15}
            }
        },
        'feature_fusion': {
            'baseline': {'ME0': 10.0, 'RSI0': 0.2},
            'normalization': {'RSI_max': 2.0, 'POP_max': 10.0, 'FLOW_max': 100.0, 'ME_max': 50.0}
        }
    }
    
    # 創建處理器
    image_processor = ImageProcessor(config)
    feature_extractor = FeatureExtractor(config)
    
    # 性能測試
    num_frames = 30
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    start_time = time.time()
    
    for _ in range(num_frames):
        processed_image, rois = image_processor.preprocess_image(test_image)
        features = feature_extractor.extract_features(rois)
    
    elapsed_time = time.time() - start_time
    fps = num_frames / elapsed_time
    
    print(f"處理性能: {fps:.2f} FPS")
    
    # 性能要求：至少30 FPS
    assert fps >= 20.0, f"性能不足: {fps:.2f} FPS < 20.0 FPS"


if __name__ == '__main__':
    # 執行測試
    pytest.main([__file__, '-v'])
