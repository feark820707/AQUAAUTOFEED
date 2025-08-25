#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI啟動腳本 - 啟動智能水產養殖自動餵料控制系統GUI

提供簡單的啟動界面，自動檢查依賴並啟動主要GUI
"""

import sys
import os
import subprocess
from pathlib import Path

# 添加項目路徑到Python路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import threading
    import time
except ImportError as e:
    print(f"缺少必要的Python模塊: {e}")
    print("請確保已安裝Python 3.8+和tkinter")
    sys.exit(1)


class LauncherGUI:
    """啟動器GUI類"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_interface()
        
        # 檢查依賴
        self.check_dependencies()
        
    def setup_window(self):
        """設置窗口"""
        self.root.title("智能水產養殖自動餵料控制系統 - 啟動器")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # 居中顯示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (400 // 2)
        self.root.geometry(f"600x400+{x}+{y}")
        
    def create_interface(self):
        """創建界面"""
        # 標題
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="智能水產養殖自動餵料控制系統",
            font=("微軟正黑體", 16, "bold")
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Intelligent Aquatic Feeding Control System",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 版本信息
        version_label = ttk.Label(title_frame, text="版本 1.0", font=("微軟正黑體", 9))
        version_label.pack(pady=(10, 0))
        
        # 系統狀態
        status_frame = ttk.LabelFrame(self.root, text="系統狀態檢查", padding=10)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_text = tk.Text(status_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 控制按鈕
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.launch_button = ttk.Button(
            button_frame,
            text="啟動主要GUI",
            command=self.launch_main_gui,
            state=tk.DISABLED
        )
        self.launch_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.config_button = ttk.Button(
            button_frame,
            text="配置編輯器",
            command=self.launch_config_editor
        )
        self.config_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.log_button = ttk.Button(
            button_frame,
            text="日誌查看器",
            command=self.launch_log_viewer
        )
        self.log_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="退出",
            command=self.root.quit
        ).pack(side=tk.LEFT)
        
        # 進度條
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=20, pady=(0, 20))
        
    def add_status(self, message, status="INFO"):
        """添加狀態消息"""
        self.status_text.configure(state=tk.NORMAL)
        
        timestamp = time.strftime("%H:%M:%S")
        status_symbols = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "WARNING": "⚠",
            "ERROR": "✗"
        }
        
        symbol = status_symbols.get(status, "•")
        full_message = f"[{timestamp}] {symbol} {message}\n"
        
        self.status_text.insert(tk.END, full_message)
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)
        
        # 更新界面
        self.root.update_idletasks()
        
    def check_dependencies(self):
        """檢查系統依賴"""
        def check_task():
            self.progress.start()
            self.add_status("開始檢查系統依賴...")
            
            # 檢查Python版本
            python_version = sys.version_info
            if python_version >= (3, 8):
                self.add_status(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}", "SUCCESS")
            else:
                self.add_status(f"Python版本過低: {python_version.major}.{python_version.minor}.{python_version.micro} (需要3.8+)", "ERROR")
                
            # 檢查必要模塊
            required_modules = [
                ("tkinter", "GUI框架"),
                ("numpy", "數值計算"),
                ("matplotlib", "圖表繪製"),
                ("pandas", "數據處理"),
                ("yaml", "配置文件解析"),
                ("cv2", "OpenCV視覺處理"),
                ("scipy", "科學計算")
            ]
            
            missing_modules = []
            
            for module_name, description in required_modules:
                try:
                    if module_name == "cv2":
                        import cv2
                        self.add_status(f"✓ {description} ({module_name}): {cv2.__version__}", "SUCCESS")
                    elif module_name == "yaml":
                        import yaml
                        self.add_status(f"✓ {description} ({module_name}): 可用", "SUCCESS")
                    else:
                        module = __import__(module_name)
                        version = getattr(module, '__version__', '未知版本')
                        self.add_status(f"✓ {description} ({module_name}): {version}", "SUCCESS")
                except ImportError:
                    self.add_status(f"✗ {description} ({module_name}): 未安裝", "ERROR")
                    missing_modules.append(module_name)
                    
            # 檢查項目文件
            self.add_status("檢查項目文件結構...")
            
            required_files = [
                "gui/main_gui.py",
                "gui/simulator.py",
                "gui/config_editor.py",
                "gui/log_viewer.py",
                "config/system_params.yaml"
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = project_root / file_path
                if full_path.exists():
                    self.add_status(f"✓ {file_path}: 存在", "SUCCESS")
                else:
                    self.add_status(f"✗ {file_path}: 缺失", "ERROR")
                    missing_files.append(file_path)
                    
            # 創建必要目錄
            directories = ["logs", "validation_results", "gui/__pycache__"]
            for directory in directories:
                dir_path = project_root / directory
                if not dir_path.exists():
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        self.add_status(f"✓ 創建目錄: {directory}", "SUCCESS")
                    except Exception as e:
                        self.add_status(f"✗ 創建目錄失敗: {directory} - {str(e)}", "ERROR")
                        
            # 檢查結果
            self.progress.stop()
            
            if missing_modules:
                self.add_status(f"缺少模塊: {', '.join(missing_modules)}", "WARNING")
                self.add_status("請運行 'pip install -r requirements.txt' 安裝依賴", "INFO")
                
            if missing_files:
                self.add_status(f"缺少文件: {', '.join(missing_files)}", "ERROR")
                self.add_status("請確保項目文件完整", "INFO")
                
            if not missing_modules and not missing_files:
                self.add_status("所有依賴檢查通過！可以啟動系統", "SUCCESS")
                self.launch_button.configure(state=tk.NORMAL)
            else:
                self.add_status("存在依賴問題，建議先解決後再啟動", "WARNING")
                # 仍然允許啟動，但會有警告
                self.launch_button.configure(state=tk.NORMAL)
                
        # 在後台線程中執行檢查
        thread = threading.Thread(target=check_task, daemon=True)
        thread.start()
        
    def launch_main_gui(self):
        """啟動主要GUI"""
        try:
            self.add_status("正在啟動主要GUI...")
            
            # 導入並啟動主GUI
            try:
                from gui.main_gui import AquaFeederGUI
                
                # 隱藏啟動器窗口
                self.root.withdraw()
                
                # 啟動主GUI
                app = AquaFeederGUI()
                
                # 設置關閉回調
                def on_main_gui_close():
                    app.on_closing()
                    self.root.deiconify()  # 重新顯示啟動器
                    
                app.root.protocol("WM_DELETE_WINDOW", on_main_gui_close)
                app.root.mainloop()
                
            except ImportError as e:
                self.add_status(f"導入主GUI失敗: {str(e)}", "ERROR")
                messagebox.showerror("錯誤", f"無法啟動主GUI:\n{str(e)}")
                
        except Exception as e:
            self.add_status(f"啟動主GUI時發生錯誤: {str(e)}", "ERROR")
            messagebox.showerror("錯誤", f"啟動失敗:\n{str(e)}")
            
    def launch_config_editor(self):
        """啟動配置編輯器"""
        try:
            from gui.config_editor import ConfigEditor
            ConfigEditor(self.root)
            self.add_status("已啟動配置編輯器", "SUCCESS")
        except Exception as e:
            self.add_status(f"啟動配置編輯器失敗: {str(e)}", "ERROR")
            messagebox.showerror("錯誤", f"無法啟動配置編輯器:\n{str(e)}")
            
    def launch_log_viewer(self):
        """啟動日誌查看器"""
        try:
            from gui.log_viewer import LogViewer
            LogViewer(self.root)
            self.add_status("已啟動日誌查看器", "SUCCESS")
        except Exception as e:
            self.add_status(f"啟動日誌查看器失敗: {str(e)}", "ERROR")
            messagebox.showerror("錯誤", f"無法啟動日誌查看器:\n{str(e)}")


def install_requirements():
    """自動安裝依賴"""
    requirements_file = project_root / "requirements.txt"
    
    if not requirements_file.exists():
        print("未找到 requirements.txt 文件")
        return False
        
    try:
        print("正在安裝依賴...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], capture_output=True, text=True, check=True)
        
        print("依賴安裝成功！")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"依賴安裝失敗: {e}")
        print(f"錯誤輸出: {e.stderr}")
        return False


def main():
    """主函數"""
    print("智能水產養殖自動餵料控制系統 v1.0")
    print("=" * 50)
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install-deps":
            install_requirements()
            return
        elif sys.argv[1] == "--main-gui":
            # 直接啟動主GUI
            try:
                from gui.main_gui import AquaFeederGUI
                app = AquaFeederGUI()
                app.root.mainloop()
            except Exception as e:
                print(f"啟動主GUI失敗: {e}")
            return
        elif sys.argv[1] == "--config":
            # 直接啟動配置編輯器
            try:
                from gui.config_editor import ConfigEditor
                app = ConfigEditor()
                app.window.mainloop()
            except Exception as e:
                print(f"啟動配置編輯器失敗: {e}")
            return
        elif sys.argv[1] == "--log":
            # 直接啟動日誌查看器
            try:
                from gui.log_viewer import LogViewer
                app = LogViewer()
                app.window.mainloop()
            except Exception as e:
                print(f"啟動日誌查看器失敗: {e}")
            return
        elif sys.argv[1] == "--help":
            print("使用方法:")
            print("  python launch_gui.py              # 啟動GUI啟動器")
            print("  python launch_gui.py --main-gui   # 直接啟動主GUI")
            print("  python launch_gui.py --config     # 直接啟動配置編輯器")
            print("  python launch_gui.py --log        # 直接啟動日誌查看器")
            print("  python launch_gui.py --install-deps # 安裝依賴")
            print("  python launch_gui.py --help       # 顯示幫助")
            return
            
    # 啟動GUI啟動器
    try:
        app = LauncherGUI()
        app.root.mainloop()
    except KeyboardInterrupt:
        print("\n程序被用戶中斷")
    except Exception as e:
        print(f"啟動器錯誤: {e}")
        input("按Enter鍵退出...")


if __name__ == "__main__":
    main()
