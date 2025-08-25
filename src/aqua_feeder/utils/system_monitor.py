"""
系統狀態監控工具
提供系統健康檢查、性能監控和狀態報告
"""

import logging
import time
import json
import psutil
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

class SystemMonitor:
    """系統監控器類"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化系統監控器
        
        Args:
            config: 系統配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 監控配置
        monitor_config = config.get('system', {}).get('monitoring', {})
        self.update_interval = monitor_config.get('update_interval', 5.0)
        self.history_size = monitor_config.get('history_size', 100)
        
        # 狀態存儲
        self.system_stats = {}
        self.status_history = []
        self.alerts = []
        
        # 閾值設定
        self.thresholds = monitor_config.get('thresholds', {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'temperature': 70.0,
            'disk_usage': 90.0
        })
        
        # 監控線程
        self.monitoring_thread = None
        self.is_monitoring = False
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            self.logger.warning("監控已在運行中")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info("系統監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
        self.logger.info("系統監控已停止")
    
    def _monitoring_loop(self):
        """監控主循環"""
        while self.is_monitoring:
            try:
                # 收集系統統計
                stats = self._collect_system_stats()
                
                # 檢查閾值並生成警報
                self._check_thresholds(stats)
                
                # 更新狀態
                with self.lock:
                    self.system_stats = stats
                    self._update_history(stats)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"監控循環錯誤: {e}")
                time.sleep(self.update_interval)
    
    def _collect_system_stats(self) -> Dict[str, Any]:
        """收集系統統計信息"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory': self._get_memory_stats(),
            'disk': self._get_disk_stats(),
            'network': self._get_network_stats(),
            'temperature': self._get_temperature(),
            'processes': self._get_process_count()
        }
        
        return stats
    
    def _get_memory_stats(self) -> Dict[str, float]:
        """獲取記憶體統計"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total / (1024**3),  # GB
            'available': memory.available / (1024**3),
            'used': memory.used / (1024**3),
            'percent': memory.percent
        }
    
    def _get_disk_stats(self) -> Dict[str, float]:
        """獲取磁碟統計"""
        disk = psutil.disk_usage('/')
        return {
            'total': disk.total / (1024**3),  # GB
            'used': disk.used / (1024**3),
            'free': disk.free / (1024**3),
            'percent': (disk.used / disk.total) * 100
        }
    
    def _get_network_stats(self) -> Dict[str, int]:
        """獲取網路統計"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
    
    def _get_temperature(self) -> Optional[float]:
        """獲取CPU溫度"""
        try:
            # 嘗試從thermal zone獲取溫度
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read().strip()) / 1000.0
                return temp
        except:
            try:
                # 使用psutil獲取溫度
                sensors = psutil.sensors_temperatures()
                if sensors:
                    for name, entries in sensors.items():
                        if entries:
                            return entries[0].current
            except:
                pass
        
        return None
    
    def _get_process_count(self) -> int:
        """獲取進程數量"""
        return len(psutil.pids())
    
    def _check_thresholds(self, stats: Dict[str, Any]):
        """檢查閾值並生成警報"""
        current_time = datetime.now()
        
        # CPU使用率檢查
        if stats['cpu_usage'] > self.thresholds['cpu_usage']:
            self._add_alert('high_cpu', f"CPU使用率過高: {stats['cpu_usage']:.1f}%")
        
        # 記憶體使用率檢查
        if stats['memory']['percent'] > self.thresholds['memory_usage']:
            self._add_alert('high_memory', f"記憶體使用率過高: {stats['memory']['percent']:.1f}%")
        
        # 磁碟使用率檢查
        if stats['disk']['percent'] > self.thresholds['disk_usage']:
            self._add_alert('high_disk', f"磁碟使用率過高: {stats['disk']['percent']:.1f}%")
        
        # 溫度檢查
        if stats['temperature'] and stats['temperature'] > self.thresholds['temperature']:
            self._add_alert('high_temperature', f"溫度過高: {stats['temperature']:.1f}°C")
    
    def _add_alert(self, alert_type: str, message: str):
        """添加警報"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'severity': 'warning'
        }
        
        with self.lock:
            self.alerts.append(alert)
            # 限制警報歷史大小
            if len(self.alerts) > self.history_size:
                self.alerts = self.alerts[-self.history_size:]
        
        self.logger.warning(f"系統警報: {message}")
    
    def _update_history(self, stats: Dict[str, Any]):
        """更新狀態歷史"""
        self.status_history.append(stats)
        # 限制歷史大小
        if len(self.status_history) > self.history_size:
            self.status_history = self.status_history[-self.history_size:]
    
    def get_current_status(self) -> Dict[str, Any]:
        """獲取當前系統狀態"""
        with self.lock:
            return self.system_stats.copy()
    
    def get_status_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        獲取狀態歷史
        
        Args:
            limit: 限制返回的記錄數量
            
        Returns:
            狀態歷史列表
        """
        with self.lock:
            history = self.status_history.copy()
            if limit:
                return history[-limit:]
            return history
    
    def get_alerts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        獲取警報列表
        
        Args:
            limit: 限制返回的警報數量
            
        Returns:
            警報列表
        """
        with self.lock:
            alerts = self.alerts.copy()
            if limit:
                return alerts[-limit:]
            return alerts
    
    def clear_alerts(self):
        """清除所有警報"""
        with self.lock:
            self.alerts.clear()
        self.logger.info("警報列表已清除")
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        獲取系統健康狀態
        
        Returns:
            健康狀態報告
        """
        stats = self.get_current_status()
        if not stats:
            return {'status': 'unknown', 'details': '無法獲取系統統計'}
        
        # 評估健康狀態
        health_score = 100
        issues = []
        
        # CPU檢查
        if stats.get('cpu_usage', 0) > self.thresholds['cpu_usage']:
            health_score -= 20
            issues.append(f"CPU使用率過高: {stats['cpu_usage']:.1f}%")
        
        # 記憶體檢查
        memory_usage = stats.get('memory', {}).get('percent', 0)
        if memory_usage > self.thresholds['memory_usage']:
            health_score -= 25
            issues.append(f"記憶體使用率過高: {memory_usage:.1f}%")
        
        # 磁碟檢查
        disk_usage = stats.get('disk', {}).get('percent', 0)
        if disk_usage > self.thresholds['disk_usage']:
            health_score -= 15
            issues.append(f"磁碟使用率過高: {disk_usage:.1f}%")
        
        # 溫度檢查
        temperature = stats.get('temperature')
        if temperature and temperature > self.thresholds['temperature']:
            health_score -= 30
            issues.append(f"溫度過高: {temperature:.1f}°C")
        
        # 確定健康狀態
        if health_score >= 80:
            status = 'healthy'
        elif health_score >= 60:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'score': max(0, health_score),
            'issues': issues,
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        }
    
    def export_data(self, filename: str):
        """
        導出監控數據
        
        Args:
            filename: 輸出文件名
        """
        try:
            data = {
                'current_status': self.get_current_status(),
                'history': self.get_status_history(),
                'alerts': self.get_alerts(),
                'health': self.get_system_health(),
                'config': {
                    'thresholds': self.thresholds,
                    'update_interval': self.update_interval
                },
                'export_time': datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"監控數據已導出到: {filename}")
            
        except Exception as e:
            self.logger.error(f"數據導出失敗: {e}")
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """
        更新閾值設定
        
        Args:
            new_thresholds: 新的閾值字典
        """
        self.thresholds.update(new_thresholds)
        self.logger.info(f"閾值已更新: {new_thresholds}")
    
    def __del__(self):
        """析構函數"""
        self.stop_monitoring()
