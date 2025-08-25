#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI測試腳本 - 測試GUI組件是否正常工作

這個腳本會逐一測試各個GUI組件，確保它們能夠正常啟動
"""

import sys
import os
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """測試模塊導入"""
    print("測試模塊導入...")
    
    try:
        import tkinter as tk
        print("✓ tkinter 導入成功")
    except ImportError as e:
        print(f"✗ tkinter 導入失敗: {e}")
        return False
        
    try:
        import numpy as np
        print(f"✓ numpy 導入成功 (版本: {np.__version__})")
    except ImportError as e:
        print(f"✗ numpy 導入失敗: {e}")
        return False
        
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        print(f"✓ matplotlib 導入成功 (版本: {matplotlib.__version__})")
    except ImportError as e:
        print(f"✗ matplotlib 導入失敗: {e}")
        return False
        
    return True

def test_gui_components():
    """測試GUI組件"""
    print("\n測試GUI組件...")
    
    # 測試模擬器
    try:
        from gui.simulator import SystemSimulator
        simulator = SystemSimulator()
        print("✓ SystemSimulator 創建成功")
        
        # 簡單測試
        simulator.start()
        data = simulator.get_current_data()
        simulator.stop()
        print(f"✓ SystemSimulator 基本功能測試通過: {data}")
        
    except Exception as e:
        print(f"✗ SystemSimulator 測試失敗: {e}")
        return False
        
    # 測試配置編輯器（不顯示窗口）
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # 隱藏主窗口
        
        from gui.config_editor import ConfigEditor
        config_editor = ConfigEditor(root)
        config_editor.window.withdraw()  # 隱藏配置編輯器窗口
        
        print("✓ ConfigEditor 創建成功")
        
        config_editor.window.destroy()
        root.destroy()
        
    except Exception as e:
        print(f"✗ ConfigEditor 測試失敗: {e}")
        return False
        
    return True

def test_file_structure():
    """測試文件結構"""
    print("\n測試文件結構...")
    
    required_files = [
        "gui/main_gui.py",
        "gui/simulator.py", 
        "gui/config_editor.py",
        "gui/log_viewer.py",
        "launch_gui.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✓ {file_path} 存在")
        else:
            print(f"✗ {file_path} 缺失")
            all_exist = False
            
    return all_exist

def create_sample_data():
    """創建示例數據文件"""
    print("\n創建示例數據...")
    
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # 創建logs目錄
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # 生成示例數據
        n_points = 1000
        base_time = datetime.now() - timedelta(hours=1)
        
        data = {
            '時間': [base_time + timedelta(seconds=i*3.6) for i in range(n_points)],
            'H值': np.random.normal(0.5, 0.1, n_points),
            'PWM': np.random.normal(45, 10, n_points),
            '狀態': np.random.choice(['餵食', '評估', '穩定'], n_points),
            'ME': np.random.normal(0.3, 0.05, n_points),
            'RSI': np.random.normal(0.4, 0.08, n_points),
            'POP': np.random.normal(0.2, 0.03, n_points),
            'FLOW': np.random.normal(0.1, 0.02, n_points)
        }
        
        df = pd.DataFrame(data)
        
        # 保存為CSV
        csv_file = logs_dir / "sample_data.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        print(f"✓ 示例數據已創建: {csv_file}")
        return True
        
    except Exception as e:
        print(f"✗ 創建示例數據失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("智能水產養殖自動餵料控制系統 - GUI測試")
    print("=" * 50)
    
    # 測試步驟
    tests = [
        ("模塊導入", test_imports),
        ("文件結構", test_file_structure), 
        ("GUI組件", test_gui_components),
        ("示例數據", create_sample_data)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} 測試時發生錯誤: {e}")
            results.append((test_name, False))
    
    # 總結
    print(f"\n{'='*20} 測試總結 {'='*20}")
    
    passed = 0
    for test_name, result in results:
        status = "通過" if result else "失敗"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{len(results)} 項測試通過")
    
    if passed == len(results):
        print("\n🎉 所有測試通過！GUI系統準備就緒。")
        print("\n可以運行以下命令啟動系統:")
        print("  python launch_gui.py              # 啟動GUI啟動器")
        print("  python launch_gui.py --main-gui   # 直接啟動主GUI")
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤信息並修復問題。")
        
    print("\n測試完成！")

if __name__ == "__main__":
    main()
