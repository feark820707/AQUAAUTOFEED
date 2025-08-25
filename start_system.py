#!/usr/bin/env python3
"""
智能餵料系統啟動腳本
執行系統檢查並啟動主控制器
"""

import os
import sys
import yaml
import logging
import subprocess
import time
from pathlib import Path

def check_system_requirements():
    """檢查系統需求"""
    print("🔍 檢查系統需求...")
    
    issues = []
    
    # 檢查Python版本
    if sys.version_info < (3, 8):
        issues.append(f"Python版本過低: {sys.version_info.major}.{sys.version_info.minor}, 需要 >= 3.8")
    else:
        print(f"✅ Python版本: {sys.version_info.major}.{sys.version_info.minor}")
    
    # 檢查必要的Python包
    required_packages = [
        'cv2', 'numpy', 'scipy', 'yaml', 'matplotlib'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安裝")
        except ImportError:
            issues.append(f"缺少Python包: {package}")
    
    # 檢查Jetson GPIO (僅在Jetson平台)
    try:
        import Jetson.GPIO as GPIO
        print("✅ Jetson.GPIO 可用")
        gpio_available = True
    except ImportError:
        print("⚠️  Jetson.GPIO 不可用 (將使用模擬模式)")
        gpio_available = False
    
    return issues, gpio_available

def check_hardware():
    """檢查硬體連接"""
    print("\n🔧 檢查硬體連接...")
    
    hardware_status = {}
    
    # 檢查相機
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ 相機正常 - 解析度: {frame.shape}")
                hardware_status['camera'] = True
            else:
                print("❌ 相機無法讀取影像")
                hardware_status['camera'] = False
            cap.release()
        else:
            print("❌ 無法開啟相機")
            hardware_status['camera'] = False
    except Exception as e:
        print(f"❌ 相機檢查錯誤: {e}")
        hardware_status['camera'] = False
    
    # 檢查GPIO (僅在Jetson平台)
    try:
        import Jetson.GPIO as GPIO
        GPIO.setmode(GPIO.BOARD)
        print("✅ GPIO系統正常")
        GPIO.cleanup()
        hardware_status['gpio'] = True
    except Exception as e:
        print(f"⚠️  GPIO檢查: {e}")
        hardware_status['gpio'] = False
    
    return hardware_status

def check_configuration():
    """檢查配置文件"""
    print("\n📋 檢查配置文件...")
    
    config_path = Path('config/system_params.yaml')
    
    if not config_path.exists():
        print("❌ 配置文件不存在: config/system_params.yaml")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 檢查必要的配置段落
        required_sections = ['hardware', 'vision', 'controller', 'feature_fusion']
        for section in required_sections:
            if section in config:
                print(f"✅ 配置段落 '{section}' 存在")
            else:
                print(f"❌ 缺少配置段落 '{section}'")
                return None
        
        print("✅ 配置文件格式正確")
        return config
        
    except Exception as e:
        print(f"❌ 配置文件錯誤: {e}")
        return None

def setup_directories():
    """設置必要的目錄"""
    print("\n📁 設置目錄結構...")
    
    directories = ['logs', 'data', 'debug_output']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ 目錄 '{directory}' 已準備")

def start_system():
    """啟動系統"""
    print("\n🚀 啟動智能餵料系統...")
    
    # 設置環境
    os.environ['PYTHONPATH'] = os.path.join(os.getcwd(), 'src')
    
    # 啟動主控制器
    try:
        from src.aqua_feeder.main_controller import AquaFeederController
        
        print("正在初始化控制器...")
        controller = AquaFeederController()
        
        print("正在啟動系統...")
        controller.start()
        
        print("\n" + "="*50)
        print("🎉 智能餵料系統已成功啟動!")
        print("="*50)
        print("📊 監控信息:")
        print("  - 系統日誌: logs/")
        print("  - 資料記錄: logs/feeding_log_YYYYMMDD.csv")
        print("  - 按 Ctrl+C 停止系統")
        print("="*50)
        
        # 保持運行
        try:
            while controller.is_running:
                time.sleep(1)
                
                # 定期顯示狀態 (每30秒)
                if int(time.time()) % 30 == 0:
                    status = controller.get_system_status()
                    print(f"📈 系統運行中 - 處理幀數: {status['stats']['total_frames']}")
                    
        except KeyboardInterrupt:
            print("\n🛑 收到停止信號...")
        
        controller.stop()
        print("✅ 系統已安全停止")
        
    except Exception as e:
        print(f"❌ 系統啟動失敗: {e}")
        return False
    
    return True

def print_banner():
    """顯示啟動橫幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║              智能水產養殖自動餵料控制系統                      ║
    ║            Intelligent Aquaculture Feeding System           ║
    ║                                                              ║
    ║  版本: v1.0.0                                                ║
    ║  平台: Jetson Nano + ROS2                                    ║
    ║  作者: AquaFeeder Team                                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """主函數"""
    print_banner()
    
    # 系統檢查
    issues, gpio_available = check_system_requirements()
    
    if issues:
        print("\n❌ 系統需求檢查失敗:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n請解決以上問題後重新啟動")
        return False
    
    # 硬體檢查
    hardware_status = check_hardware()
    
    # 配置檢查
    config = check_configuration()
    if config is None:
        print("\n❌ 配置檢查失敗，無法啟動系統")
        return False
    
    # 設置目錄
    setup_directories()
    
    # 最終確認
    print("\n" + "="*50)
    print("📋 系統準備就緒:")
    print(f"  - 相機: {'✅' if hardware_status.get('camera') else '❌'}")
    print(f"  - GPIO: {'✅' if hardware_status.get('gpio') else '⚠️ 模擬模式'}")
    print(f"  - 配置: ✅")
    print("="*50)
    
    # 詢問是否啟動
    if hardware_status.get('camera'):
        response = input("\n是否啟動系統? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            return start_system()
        else:
            print("👋 啟動已取消")
            return False
    else:
        print("\n⚠️  相機未連接，無法啟動完整系統")
        print("請檢查相機連接後重新運行")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 啟動已中止")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 啟動錯誤: {e}")
        sys.exit(1)
