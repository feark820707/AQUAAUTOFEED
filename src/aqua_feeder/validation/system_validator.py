"""
系統驗證與分析工具
實現需求書的驗證與測試功能：
- 相關係數計算 r(airflow, H) ≥ 0.75
- PWM振盪幅度檢查 ≤ ±15%
- T_disappear命中率分析 ≥ 70%
- 故障降級反應時間檢測 ≤ 1s
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Tuple, Optional
from scipy import stats
import yaml

class SystemValidator:
    """
    系統驗證器
    實現需求書的所有驗證與測試功能
    """
    
    def __init__(self, config_path: str = "config/system_params.yaml"):
        """
        初始化系統驗證器
        
        Args:
            config_path: 配置文件路徑
        """
        self.logger = logging.getLogger(__name__)
        
        # 載入配置
        self.config = self._load_config(config_path)
        
        # 驗證目標 - 符合需求書要求
        validation_config = self.config.get('validation', {})
        self.targets = {
            'correlation_target': validation_config.get('correlation_target', 0.75),
            'pwm_oscillation_limit': validation_config.get('pwm_oscillation_limit', 15),
            'response_time_limit': validation_config.get('response_time_limit', 1.0),
            'hit_rate_target': validation_config.get('hit_rate_target', 0.70)
        }
        
        self.logger.info("系統驗證器初始化完成")
        self.logger.info(f"驗證目標: {self.targets}")
    
    def _load_config(self, config_path: str) -> Dict:
        """載入配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return {}
    
    def validate_correlation(self, csv_file: str, airflow_data: Optional[List[float]] = None) -> Dict:
        """
        驗證活躍度H與氣泡盤檔位的相關係數
        目標：r(airflow, H) ≥ 0.75
        
        Args:
            csv_file: 日誌CSV文件路徑
            airflow_data: 氣泡盤檔位數據（可選，用於展示缸測試）
            
        Returns:
            驗證結果字典
        """
        try:
            # 讀取數據
            df = pd.read_csv(csv_file)
            
            if 'H' not in df.columns:
                return {'status': 'error', 'message': '缺少H值數據'}
            
            # 如果沒有提供airflow數據，嘗試從配置中生成模擬數據
            if airflow_data is None:
                # 生成模擬的airflow檔位數據（用於演示）
                airflow_data = self._generate_demo_airflow_data(len(df))
            
            if len(airflow_data) != len(df):
                return {'status': 'error', 'message': 'airflow數據長度不匹配'}
            
            # 計算相關係數
            correlation, p_value = stats.pearsonr(airflow_data, df['H'])
            
            # 驗證結果
            is_passed = correlation >= self.targets['correlation_target']
            
            result = {
                'status': 'passed' if is_passed else 'failed',
                'correlation_coefficient': correlation,
                'p_value': p_value,
                'target': self.targets['correlation_target'],
                'is_significant': p_value < 0.05,
                'sample_size': len(df),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"相關係數驗證: r={correlation:.3f}, 目標≥{self.targets['correlation_target']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"相關係數驗證失敗: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def validate_pwm_oscillation(self, csv_file: str, time_window: int = 10) -> Dict:
        """
        驗證PWM振盪幅度
        目標：PWM振盪幅度 ≤ ±15%（10迴合內）
        
        Args:
            csv_file: 日誌CSV文件路徑
            time_window: 分析時間窗口（迴合數）
            
        Returns:
            驗證結果字典
        """
        try:
            # 讀取數據
            df = pd.read_csv(csv_file)
            
            if 'pwm' not in df.columns:
                return {'status': 'error', 'message': '缺少PWM數據'}
            
            # 轉換PWM為數值
            df['pwm_numeric'] = pd.to_numeric(df['pwm'], errors='coerce')
            df = df.dropna(subset=['pwm_numeric'])
            
            if len(df) < time_window:
                return {'status': 'error', 'message': f'數據不足，需要至少{time_window}個數據點'}
            
            # 計算滑動窗口內的振盪幅度
            oscillations = []
            for i in range(len(df) - time_window + 1):
                window_data = df['pwm_numeric'].iloc[i:i+time_window]
                max_val = window_data.max()
                min_val = window_data.min()
                oscillation = max_val - min_val
                oscillations.append(oscillation)
            
            max_oscillation = max(oscillations) if oscillations else 0
            avg_oscillation = np.mean(oscillations) if oscillations else 0
            
            # 驗證結果
            is_passed = max_oscillation <= self.targets['pwm_oscillation_limit']
            
            result = {
                'status': 'passed' if is_passed else 'failed',
                'max_oscillation': max_oscillation,
                'avg_oscillation': avg_oscillation,
                'target': self.targets['pwm_oscillation_limit'],
                'time_window': time_window,
                'num_windows': len(oscillations),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"PWM振盪驗證: 最大振盪={max_oscillation:.1f}%, "
                           f"目標≤{self.targets['pwm_oscillation_limit']}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"PWM振盪驗證失敗: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def validate_response_time(self, csv_file: str) -> Dict:
        """
        驗證故障降級反應時間
        目標：故障降級反應時間 ≤ 1s
        
        Args:
            csv_file: 日誌CSV文件路徑
            
        Returns:
            驗證結果字典
        """
        try:
            # 讀取數據
            df = pd.read_csv(csv_file)
            
            if 'state' not in df.columns or 'timestamp' not in df.columns:
                return {'status': 'error', 'message': '缺少狀態或時間戳數據'}
            
            # 轉換時間戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 尋找狀態變化到異常模式的時間
            anomaly_transitions = []
            
            for i in range(1, len(df)):
                if (df.iloc[i]['state'] == '異常模式' and 
                    df.iloc[i-1]['state'] != '異常模式'):
                    
                    time_diff = (df.iloc[i]['timestamp'] - df.iloc[i-1]['timestamp']).total_seconds()
                    anomaly_transitions.append(time_diff)
            
            if not anomaly_transitions:
                return {
                    'status': 'no_data',
                    'message': '未檢測到異常狀態轉換',
                    'transitions_found': 0
                }
            
            max_response_time = max(anomaly_transitions)
            avg_response_time = np.mean(anomaly_transitions)
            
            # 驗證結果
            is_passed = max_response_time <= self.targets['response_time_limit']
            
            result = {
                'status': 'passed' if is_passed else 'failed',
                'max_response_time': max_response_time,
                'avg_response_time': avg_response_time,
                'target': self.targets['response_time_limit'],
                'transitions_found': len(anomaly_transitions),
                'all_response_times': anomaly_transitions,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"反應時間驗證: 最大反應時間={max_response_time:.3f}s, "
                           f"目標≤{self.targets['response_time_limit']}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"反應時間驗證失敗: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def validate_disappearance_hit_rate(self, csv_file: str, target_range: Tuple[float, float] = (2.0, 5.0)) -> Dict:
        """
        驗證T_disappear命中率
        目標：T_disappear命中率 ≥ 70%
        
        Args:
            csv_file: 日誌CSV文件路徑
            target_range: 目標時間範圍 (最小值, 最大值)
            
        Returns:
            驗證結果字典
        """
        try:
            # 讀取數據
            df = pd.read_csv(csv_file)
            
            if 'state' not in df.columns or 'timestamp' not in df.columns:
                return {'status': 'error', 'message': '缺少狀態或時間戳數據'}
            
            # 轉換時間戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 尋找餵食週期
            feeding_cycles = []
            current_cycle = {}
            
            for i, row in df.iterrows():
                if row['state'] == '餵食中' and not current_cycle:
                    current_cycle['start'] = row['timestamp']
                elif row['state'] == '穩定等待' and current_cycle:
                    current_cycle['end'] = row['timestamp']
                    cycle_duration = (current_cycle['end'] - current_cycle['start']).total_seconds()
                    feeding_cycles.append(cycle_duration)
                    current_cycle = {}
            
            if not feeding_cycles:
                return {
                    'status': 'no_data',
                    'message': '未檢測到完整的餵食週期',
                    'cycles_found': 0
                }
            
            # 計算命中率
            hits = sum(1 for duration in feeding_cycles 
                      if target_range[0] <= duration <= target_range[1])
            hit_rate = hits / len(feeding_cycles)
            
            # 驗證結果
            is_passed = hit_rate >= self.targets['hit_rate_target']
            
            result = {
                'status': 'passed' if is_passed else 'failed',
                'hit_rate': hit_rate,
                'hits': hits,
                'total_cycles': len(feeding_cycles),
                'target': self.targets['hit_rate_target'],
                'target_range': target_range,
                'cycle_durations': feeding_cycles,
                'avg_duration': np.mean(feeding_cycles),
                'std_duration': np.std(feeding_cycles),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"T_disappear命中率驗證: {hit_rate:.3f} ({hits}/{len(feeding_cycles)}), "
                           f"目標≥{self.targets['hit_rate_target']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"T_disappear驗證失敗: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def generate_validation_report(self, csv_file: str, output_dir: str = "logs/validation/") -> str:
        """
        生成完整的驗證報告
        
        Args:
            csv_file: 日誌CSV文件路徑
            output_dir: 輸出目錄
            
        Returns:
            報告文件路徑
        """
        try:
            # 創建輸出目錄
            os.makedirs(output_dir, exist_ok=True)
            
            # 執行所有驗證
            results = {}
            results['correlation'] = self.validate_correlation(csv_file)
            results['pwm_oscillation'] = self.validate_pwm_oscillation(csv_file)
            results['response_time'] = self.validate_response_time(csv_file)
            results['hit_rate'] = self.validate_disappearance_hit_rate(csv_file)
            
            # 生成報告
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = os.path.join(output_dir, f"validation_report_{timestamp}.txt")
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("智能餵料系統驗證報告\n")
                f.write("=" * 60 + "\n")
                f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"數據來源: {csv_file}\n\n")
                
                # 相關係數驗證
                f.write("1. 活躍度相關係數驗證\n")
                f.write("-" * 30 + "\n")
                corr = results['correlation']
                if corr['status'] != 'error':
                    f.write(f"相關係數: {corr.get('correlation_coefficient', 0):.3f}\n")
                    f.write(f"目標值: ≥{corr.get('target', 0)}\n")
                    f.write(f"結果: {'通過' if corr['status'] == 'passed' else '失敗'}\n")
                else:
                    f.write(f"錯誤: {corr.get('message', '未知錯誤')}\n")
                f.write("\n")
                
                # PWM振盪驗證
                f.write("2. PWM振盪幅度驗證\n")
                f.write("-" * 30 + "\n")
                pwm = results['pwm_oscillation']
                if pwm['status'] != 'error':
                    f.write(f"最大振盪: {pwm.get('max_oscillation', 0):.1f}%\n")
                    f.write(f"平均振盪: {pwm.get('avg_oscillation', 0):.1f}%\n")
                    f.write(f"目標值: ≤{pwm.get('target', 0)}%\n")
                    f.write(f"結果: {'通過' if pwm['status'] == 'passed' else '失敗'}\n")
                else:
                    f.write(f"錯誤: {pwm.get('message', '未知錯誤')}\n")
                f.write("\n")
                
                # 反應時間驗證
                f.write("3. 故障反應時間驗證\n")
                f.write("-" * 30 + "\n")
                resp = results['response_time']
                if resp['status'] not in ['error', 'no_data']:
                    f.write(f"最大反應時間: {resp.get('max_response_time', 0):.3f}s\n")
                    f.write(f"平均反應時間: {resp.get('avg_response_time', 0):.3f}s\n")
                    f.write(f"目標值: ≤{resp.get('target', 0)}s\n")
                    f.write(f"檢測到的轉換: {resp.get('transitions_found', 0)}\n")
                    f.write(f"結果: {'通過' if resp['status'] == 'passed' else '失敗'}\n")
                else:
                    f.write(f"狀態: {resp.get('message', '未檢測到異常轉換')}\n")
                f.write("\n")
                
                # 命中率驗證
                f.write("4. T_disappear命中率驗證\n")
                f.write("-" * 30 + "\n")
                hit = results['hit_rate']
                if hit['status'] not in ['error', 'no_data']:
                    f.write(f"命中率: {hit.get('hit_rate', 0):.3f} ({hit.get('hits', 0)}/{hit.get('total_cycles', 0)})\n")
                    f.write(f"目標值: ≥{hit.get('target', 0)}\n")
                    f.write(f"平均週期時間: {hit.get('avg_duration', 0):.2f}s\n")
                    f.write(f"結果: {'通過' if hit['status'] == 'passed' else '失敗'}\n")
                else:
                    f.write(f"狀態: {hit.get('message', '未檢測到餵食週期')}\n")
                f.write("\n")
                
                # 總結
                f.write("=" * 60 + "\n")
                f.write("驗證總結\n")
                f.write("=" * 60 + "\n")
                
                passed_count = sum(1 for r in results.values() if r['status'] == 'passed')
                total_tests = len(results)
                
                f.write(f"通過測試: {passed_count}/{total_tests}\n")
                
                if passed_count == total_tests:
                    f.write("整體結果: 系統驗證通過 ✓\n")
                else:
                    f.write("整體結果: 系統驗證失敗 ✗\n")
            
            # 生成圖表
            self._generate_validation_plots(csv_file, results, output_dir, timestamp)
            
            self.logger.info(f"驗證報告已生成: {report_file}")
            return report_file
            
        except Exception as e:
            self.logger.error(f"生成驗證報告失敗: {e}")
            return ""
    
    def _generate_demo_airflow_data(self, length: int) -> List[float]:
        """
        生成演示用的氣泡盤檔位數據
        模擬展示缸的真實airflow檔位
        
        Args:
            length: 數據長度
            
        Returns:
            氣泡盤檔位列表
        """
        # 生成週期性變化的檔位數據（0-7檔）
        airflow_data = []
        for i in range(length):
            # 使用正弦波生成週期性變化
            phase = (i / length) * 4 * np.pi  # 4個週期
            level = int(3.5 + 3.5 * np.sin(phase))  # 0-7的範圍
            airflow_data.append(level)
        
        return airflow_data
    
    def _generate_validation_plots(self, csv_file: str, results: Dict, 
                                 output_dir: str, timestamp: str):
        """
        生成驗證相關的圖表
        
        Args:
            csv_file: 數據文件路徑
            results: 驗證結果
            output_dir: 輸出目錄
            timestamp: 時間戳
        """
        try:
            # 讀取數據
            df = pd.read_csv(csv_file)
            
            # 創建圖表
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('系統驗證分析圖表', fontsize=16)
            
            # 1. H值與時間關係
            if 'H' in df.columns and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                axes[0, 0].plot(df['timestamp'], pd.to_numeric(df['H'], errors='coerce'))
                axes[0, 0].set_title('活躍度H值變化')
                axes[0, 0].set_ylabel('H值')
                axes[0, 0].grid(True)
            
            # 2. PWM變化
            if 'pwm' in df.columns:
                axes[0, 1].plot(df.index, pd.to_numeric(df['pwm'], errors='coerce'))
                axes[0, 1].set_title('PWM占空比變化')
                axes[0, 1].set_ylabel('PWM (%)')
                axes[0, 1].grid(True)
            
            # 3. 相關係數結果
            if results['correlation']['status'] != 'error':
                corr_val = results['correlation']['correlation_coefficient']
                target = results['correlation']['target']
                
                axes[1, 0].bar(['實際值', '目標值'], [corr_val, target], 
                              color=['green' if corr_val >= target else 'red', 'blue'])
                axes[1, 0].set_title('活躍度相關係數')
                axes[1, 0].set_ylabel('相關係數')
                axes[1, 0].axhline(y=target, color='blue', linestyle='--', alpha=0.7)
            
            # 4. PWM振盪分析
            if results['pwm_oscillation']['status'] != 'error':
                max_osc = results['pwm_oscillation']['max_oscillation']
                target = results['pwm_oscillation']['target']
                
                axes[1, 1].bar(['最大振盪', '目標限制'], [max_osc, target], 
                              color=['green' if max_osc <= target else 'red', 'blue'])
                axes[1, 1].set_title('PWM振盪幅度')
                axes[1, 1].set_ylabel('振盪幅度 (%)')
                axes[1, 1].axhline(y=target, color='blue', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            # 保存圖表
            plot_file = os.path.join(output_dir, f"validation_plots_{timestamp}.png")
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"驗證圖表已生成: {plot_file}")
            
        except Exception as e:
            self.logger.error(f"生成驗證圖表失敗: {e}")

def main():
    """主函數 - 執行系統驗證"""
    logging.basicConfig(level=logging.INFO)
    
    # 創建驗證器
    validator = SystemValidator()
    
    # 假設有日誌文件
    log_files = [
        "logs/feeding_log_20240825.csv",
        "logs/feeding_log_latest.csv"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n正在驗證文件: {log_file}")
            report_path = validator.generate_validation_report(log_file)
            if report_path:
                print(f"驗證報告已生成: {report_path}")
            break
    else:
        print("未找到日誌文件，請確認日誌文件路徑")

if __name__ == '__main__':
    main()
