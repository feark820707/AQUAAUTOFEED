#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent Aquaculture Auto-Feeding Control System - Main GUI Interface

Complete system control, monitoring and parameter adjustment functions
Support simulation mode for PC testing
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import numpy as np
import threading
import time
import csv
import os
from datetime import datetime
import json
import cv2
from PIL import Image, ImageTk

# Import system modules (using simulation version)
from gui.simulator import SystemSimulator
from gui.config_editor import ConfigEditor
from gui.log_viewer import LogViewer


class AquaFeederGUI:
    """智能餵料系統主要GUI界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        
        # 系統狀態
        self.is_running = False
        self.simulator = SystemSimulator()
        
        # 數據存儲
        self.time_data = []
        self.h_data = []
        self.pwm_data = []
        self.feature_data = {'ME': [], 'RSI': [], 'POP': [], 'FLOW': []}
        
        # 創建界面組件
        self.create_menu()
        self.create_main_interface()
        self.create_status_bar()
        
        # 啟動數據更新
        self.update_timer = None
        self.start_data_update()
        
    def setup_main_window(self):
        """設置主窗口"""
        self.root.title("智能水產養殖自動餵料控制系統 v1.0")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 設置主題
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定義顏色
        style.configure('Title.TLabel', font=('微軟正黑體', 14, 'bold'))
        style.configure('Header.TLabel', font=('微軟正黑體', 10, 'bold'))
        style.configure('Status.TLabel', font=('Consolas', 9))
        
    def create_menu(self):
        """創建菜單欄"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜單
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="開啟配置", command=self.open_config)
        file_menu.add_command(label="保存配置", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="匯出數據", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 系統菜單
        system_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="系統", menu=system_menu)
        system_menu.add_command(label="系統配置", command=self.open_config_editor)
        system_menu.add_command(label="日誌查看", command=self.open_log_viewer)
        system_menu.add_command(label="相機測試", command=self.test_camera)
        system_menu.add_command(label="PWM測試", command=self.test_pwm)
        
        # 幫助菜單
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="幫助", menu=help_menu)
        help_menu.add_command(label="使用說明", command=self.show_help)
        help_menu.add_command(label="關於", command=self.show_about)
        
    def create_main_interface(self):
        """創建主要界面"""
        # 主要容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左側面板：控制與狀態
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 右側面板：圖表顯示
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.create_control_panel(left_frame)
        self.create_chart_panel(right_frame)
        
    def create_control_panel(self, parent):
        """創建控制面板"""
        # 系統控制區
        control_group = ttk.LabelFrame(parent, text="系統控制", padding=10)
        control_group.pack(fill=tk.X, pady=(0, 10))
        
        # 啟動/停止按鈕
        self.start_button = ttk.Button(
            control_group, 
            text="啟動系統", 
            command=self.toggle_system,
            style='Accent.TButton'
        )
        self.start_button.pack(fill=tk.X, pady=(0, 5))
        
        # 模式選擇
        mode_frame = ttk.Frame(control_group)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(mode_frame, text="運行模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="模擬模式")
        mode_combo = ttk.Combobox(
            mode_frame, 
            textvariable=self.mode_var,
            values=["模擬模式", "硬體模式"],
            state="readonly"
        )
        mode_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 系統狀態區
        status_group = ttk.LabelFrame(parent, text="系統狀態", padding=10)
        status_group.pack(fill=tk.X, pady=(0, 10))
        
        # 狀態指示燈
        status_frame = ttk.Frame(status_group)
        status_frame.pack(fill=tk.X)
        
        self.status_labels = {}
        status_items = [
            ("系統狀態", "已停止"),
            ("餵料狀態", "待機"),
            ("相機狀態", "未連接"),
            ("PWM狀態", "未初始化")
        ]
        
        for i, (label, value) in enumerate(status_items):
            row = ttk.Frame(status_frame)
            row.pack(fill=tk.X, pady=2)
            
            ttk.Label(row, text=f"{label}:", width=12).pack(side=tk.LEFT)
            status_label = ttk.Label(row, text=value, style='Status.TLabel')
            status_label.pack(side=tk.LEFT)
            self.status_labels[label] = status_label
            
            # 狀態指示燈
            indicator = tk.Canvas(row, width=12, height=12)
            indicator.pack(side=tk.RIGHT)
            indicator.create_oval(2, 2, 10, 10, fill='red', outline='darkred')
            self.status_labels[f"{label}_indicator"] = indicator
        
        # 實時數據區
        data_group = ttk.LabelFrame(parent, text="實時數據", padding=10)
        data_group.pack(fill=tk.X, pady=(0, 10))
        
        self.data_labels = {}
        data_items = [
            ("活躍度 H", "0.000"),
            ("PWM輸出", "0%"),
            ("FPS", "0"),
            ("特徵ME", "0.000"),
            ("特徵RSI", "0.000"),
            ("特徵POP", "0.000"),
            ("特徵FLOW", "0.000")
        ]
        
        for i, (label, value) in enumerate(data_items):
            row = ttk.Frame(data_group)
            row.pack(fill=tk.X, pady=1)
            
            ttk.Label(row, text=f"{label}:", width=12).pack(side=tk.LEFT)
            data_label = ttk.Label(row, text=value, style='Status.TLabel')
            data_label.pack(side=tk.RIGHT)
            self.data_labels[label] = data_label
        
        # 參數調整區
        params_group = ttk.LabelFrame(parent, text="快速參數調整", padding=10)
        params_group.pack(fill=tk.X, pady=(0, 10))
        
        # 創建參數滑桿
        self.param_vars = {}
        param_configs = [
            ("H_hi", "高活躍門檻", 0.65, 0.5, 1.0, 0.01),
            ("H_lo", "低活躍門檻", 0.35, 0.0, 0.8, 0.01),
            ("Kp", "比例增益", 15.0, 1.0, 50.0, 0.1),
            ("Ki", "積分增益", 2.0, 0.1, 10.0, 0.1),
        ]
        
        for param, label, default, min_val, max_val, resolution in param_configs:
            self.create_param_slider(params_group, param, label, default, min_val, max_val, resolution)
        
        # 手動控制區
        manual_group = ttk.LabelFrame(parent, text="手動控制", padding=10)
        manual_group.pack(fill=tk.X)
        
        # PWM手動控制
        pwm_frame = ttk.Frame(manual_group)
        pwm_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(pwm_frame, text="PWM輸出:").pack(side=tk.LEFT)
        
        self.manual_pwm_var = tk.DoubleVar(value=20)
        pwm_scale = ttk.Scale(
            pwm_frame, 
            from_=20, to=70, 
            variable=self.manual_pwm_var,
            orient=tk.HORIZONTAL,
            command=self.on_manual_pwm_change
        )
        pwm_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        
        self.pwm_value_label = ttk.Label(pwm_frame, text="20%")
        self.pwm_value_label.pack(side=tk.RIGHT)
        
        # 手動餵食按鈕
        feed_button = ttk.Button(
            manual_group,
            text="手動餵食 (3秒)",
            command=self.manual_feed
        )
        feed_button.pack(fill=tk.X, pady=(5, 0))
        
    def create_param_slider(self, parent, param, label, default, min_val, max_val, resolution):
        """創建參數調整滑桿"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
        
        var = tk.DoubleVar(value=default)
        self.param_vars[param] = var
        
        scale = ttk.Scale(
            frame,
            from_=min_val, to=max_val,
            variable=var,
            orient=tk.HORIZONTAL,
            command=lambda val, p=param: self.on_param_change(p, val)
        )
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        value_label = ttk.Label(frame, text=f"{default:.2f}", width=6)
        value_label.pack(side=tk.RIGHT)
        self.param_vars[f"{param}_label"] = value_label
        
    def create_chart_panel(self, parent):
        """創建圖表面板"""
        # 創建筆記本控件用於多頁圖表
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 主要圖表頁面
        main_chart_frame = ttk.Frame(notebook)
        notebook.add(main_chart_frame, text="主要圖表")
        
        # 特徵分析頁面
        feature_chart_frame = ttk.Frame(notebook)
        notebook.add(feature_chart_frame, text="特徵分析")
        
        # 系統分析頁面
        system_chart_frame = ttk.Frame(notebook)
        notebook.add(system_chart_frame, text="系統分析")
        
        self.create_main_charts(main_chart_frame)
        self.create_feature_charts(feature_chart_frame)
        self.create_system_charts(system_chart_frame)
        
    def create_main_charts(self, parent):
        """創建主要圖表"""
        # 創建matplotlib圖形
        self.main_fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.main_fig.patch.set_facecolor('white')
        
        # 活躍度H與PWM輸出圖表
        self.ax1.set_title('活躍度 H 與 PWM 輸出', fontsize=12, fontweight='bold')
        self.ax1.set_xlabel('時間 (秒)')
        self.ax1.set_ylabel('值', color='blue')
        self.ax1.tick_params(axis='y', labelcolor='blue')
        
        # 創建雙Y軸
        self.ax1_twin = self.ax1.twinx()
        self.ax1_twin.set_ylabel('PWM (%)', color='red')
        self.ax1_twin.tick_params(axis='y', labelcolor='red')
        
        # 初始化線條
        self.h_line, = self.ax1.plot([], [], 'b-', label='活躍度 H', linewidth=2)
        self.pwm_line, = self.ax1_twin.plot([], [], 'r-', label='PWM輸出', linewidth=2)
        
        # 添加門檻線
        self.h_hi_line = self.ax1.axhline(y=0.65, color='green', linestyle='--', alpha=0.7, label='H_hi')
        self.h_lo_line = self.ax1.axhline(y=0.35, color='orange', linestyle='--', alpha=0.7, label='H_lo')
        
        self.ax1.legend(loc='upper left')
        self.ax1_twin.legend(loc='upper right')
        self.ax1.grid(True, alpha=0.3)
        
        # 系統狀態圖表
        self.ax2.set_title('系統狀態監控', fontsize=12, fontweight='bold')
        self.ax2.set_xlabel('時間 (秒)')
        self.ax2.set_ylabel('狀態')
        
        # 狀態數據（0:停止, 1:餵食, 2:評估, 3:穩定）
        self.state_line, = self.ax2.plot([], [], 'g-', marker='o', markersize=4, label='系統狀態')
        self.ax2.set_ylim(-0.5, 3.5)
        self.ax2.set_yticks([0, 1, 2, 3])
        self.ax2.set_yticklabels(['停止', '餵食', '評估', '穩定'])
        self.ax2.legend()
        self.ax2.grid(True, alpha=0.3)
        
        # 設置圖表布局
        self.main_fig.tight_layout()
        
        # 嵌入tkinter
        self.main_canvas = FigureCanvasTkAgg(self.main_fig, parent)
        self.main_canvas.draw()
        self.main_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_feature_charts(self, parent):
        """創建特徵分析圖表"""
        # 特徵圖表
        self.feature_fig, self.feature_axes = plt.subplots(2, 2, figsize=(12, 8))
        self.feature_fig.patch.set_facecolor('white')
        
        feature_names = ['ME', 'RSI', 'POP', 'FLOW']
        feature_labels = ['動態能量', '波紋頻譜指數', '破泡事件率', '光流不一致度']
        colors = ['blue', 'green', 'red', 'purple']
        
        self.feature_lines = {}
        
        for i, (name, label, color) in enumerate(zip(feature_names, feature_labels, colors)):
            ax = self.feature_axes[i//2, i%2]
            ax.set_title(f'{label} ({name})', fontsize=10, fontweight='bold')
            ax.set_xlabel('時間 (秒)')
            ax.set_ylabel('值')
            
            line, = ax.plot([], [], color=color, linewidth=2)
            self.feature_lines[name] = line
            
            ax.grid(True, alpha=0.3)
        
        self.feature_fig.tight_layout()
        
        # 嵌入tkinter
        self.feature_canvas = FigureCanvasTkAgg(self.feature_fig, parent)
        self.feature_canvas.draw()
        self.feature_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_system_charts(self, parent):
        """創建系統分析圖表"""
        # 系統性能圖表
        self.system_fig, (self.perf_ax, self.corr_ax) = plt.subplots(1, 2, figsize=(12, 8))
        self.system_fig.patch.set_facecolor('white')
        
        # 性能指標圖表
        self.perf_ax.set_title('系統性能指標', fontsize=12, fontweight='bold')
        
        # 相關性分析圖表
        self.corr_ax.set_title('H值與PWM相關性', fontsize=12, fontweight='bold')
        self.corr_ax.set_xlabel('活躍度 H')
        self.corr_ax.set_ylabel('PWM輸出 (%)')
        
        self.system_fig.tight_layout()
        
        # 嵌入tkinter
        self.system_canvas = FigureCanvasTkAgg(self.system_fig, parent)
        self.system_canvas.draw()
        self.system_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        """創建狀態欄"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        
        # 狀態訊息
        self.status_text = tk.StringVar(value="系統已就緒")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_text)
        status_label.pack(side=tk.LEFT)
        
        # 時間顯示
        self.time_text = tk.StringVar()
        time_label = ttk.Label(self.status_bar, textvariable=self.time_text)
        time_label.pack(side=tk.RIGHT)
        
        # 更新時間
        self.update_time()
        
    def update_time(self):
        """更新時間顯示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_text.set(current_time)
        self.root.after(1000, self.update_time)
        
    def toggle_system(self):
        """切換系統啟動/停止"""
        if not self.is_running:
            self.start_system()
        else:
            self.stop_system()
            
    def start_system(self):
        """啟動系統"""
        try:
            # 更新參數到模擬器
            self.update_simulator_params()
            
            # 啟動模擬器
            self.simulator.start()
            
            self.is_running = True
            self.start_button.configure(text="停止系統")
            
            # 更新狀態
            self.update_status("系統狀態", "運行中", "green")
            self.update_status("餵料狀態", "自動模式", "green")
            self.update_status("相機狀態", "已連接", "green")
            self.update_status("PWM狀態", "已初始化", "green")
            
            self.status_text.set("系統已啟動 - 模擬模式運行中")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"系統啟動失敗: {str(e)}")
            
    def stop_system(self):
        """停止系統"""
        try:
            self.simulator.stop()
            
            self.is_running = False
            self.start_button.configure(text="啟動系統")
            
            # 更新狀態
            self.update_status("系統狀態", "已停止", "red")
            self.update_status("餵料狀態", "待機", "gray")
            self.update_status("相機狀態", "未連接", "red")
            self.update_status("PWM狀態", "未初始化", "red")
            
            self.status_text.set("系統已停止")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"系統停止失敗: {str(e)}")
            
    def update_status(self, label, text, color):
        """更新狀態顯示"""
        self.status_labels[label].configure(text=text)
        
        # 更新狀態指示燈
        indicator = self.status_labels[f"{label}_indicator"]
        indicator.delete("all")
        
        color_map = {
            "green": ("#00ff00", "#008000"),
            "red": ("#ff0000", "#800000"),
            "gray": ("#808080", "#404040"),
            "yellow": ("#ffff00", "#808000")
        }
        
        fill_color, outline_color = color_map.get(color, ("#ff0000", "#800000"))
        indicator.create_oval(2, 2, 10, 10, fill=fill_color, outline=outline_color)
        
    def update_simulator_params(self):
        """更新模擬器參數"""
        params = {}
        for param, var in self.param_vars.items():
            if not param.endswith('_label'):
                params[param] = var.get()
        
        self.simulator.update_params(params)
        
    def on_param_change(self, param, value):
        """參數變更回調"""
        float_val = float(value)
        self.param_vars[f"{param}_label"].configure(text=f"{float_val:.2f}")
        
        if self.is_running:
            # 實時更新模擬器參數
            self.simulator.update_param(param, float_val)
            
            # 更新圖表門檻線
            if param == "H_hi":
                self.h_hi_line.set_ydata([float_val, float_val])
                self.main_canvas.draw_idle()
            elif param == "H_lo":
                self.h_lo_line.set_ydata([float_val, float_val])
                self.main_canvas.draw_idle()
                
    def on_manual_pwm_change(self, value):
        """手動PWM變更回調"""
        pwm_val = float(value)
        self.pwm_value_label.configure(text=f"{pwm_val:.0f}%")
        
        if self.is_running:
            self.simulator.set_manual_pwm(pwm_val)
            
    def manual_feed(self):
        """手動餵食"""
        if self.is_running:
            self.simulator.trigger_manual_feed()
            self.status_text.set("手動餵食中...")
            self.root.after(3000, lambda: self.status_text.set("手動餵食完成"))
        else:
            messagebox.showwarning("警告", "請先啟動系統")
            
    def start_data_update(self):
        """開始數據更新"""
        self.update_data()
        
    def update_data(self):
        """更新顯示數據"""
        if self.is_running:
            # 從模擬器獲取最新數據
            data = self.simulator.get_current_data()
            
            # 更新數據標籤
            self.data_labels["活躍度 H"].configure(text=f"{data['H']:.3f}")
            self.data_labels["PWM輸出"].configure(text=f"{data['PWM']:.0f}%")
            self.data_labels["FPS"].configure(text=f"{data['FPS']:.0f}")
            self.data_labels["特徵ME"].configure(text=f"{data['ME']:.3f}")
            self.data_labels["特徵RSI"].configure(text=f"{data['RSI']:.3f}")
            self.data_labels["特徵POP"].configure(text=f"{data['POP']:.3f}")
            self.data_labels["特徵FLOW"].configure(text=f"{data['FLOW']:.3f}")
            
            # 更新圖表數據
            current_time = len(self.time_data) * 0.1  # 100ms間隔
            self.time_data.append(current_time)
            self.h_data.append(data['H'])
            self.pwm_data.append(data['PWM'])
            
            for feature in ['ME', 'RSI', 'POP', 'FLOW']:
                self.feature_data[feature].append(data[feature])
            
            # 限制數據長度（顯示最近10分鐘）
            max_points = 6000  # 10分鐘 * 60秒 * 10點/秒
            if len(self.time_data) > max_points:
                self.time_data = self.time_data[-max_points:]
                self.h_data = self.h_data[-max_points:]
                self.pwm_data = self.pwm_data[-max_points:]
                for feature in self.feature_data:
                    self.feature_data[feature] = self.feature_data[feature][-max_points:]
            
            # 更新圖表
            self.update_charts()
            
        # 排程下次更新
        self.update_timer = self.root.after(100, self.update_data)  # 100ms更新
        
    def update_charts(self):
        """更新圖表顯示"""
        if not self.time_data:
            return
            
        # 更新主要圖表
        self.h_line.set_data(self.time_data, self.h_data)
        self.pwm_line.set_data(self.time_data, self.pwm_data)
        
        # 設置軸範圍
        if len(self.time_data) > 1:
            self.ax1.set_xlim(self.time_data[0], self.time_data[-1])
            self.ax1_twin.set_xlim(self.time_data[0], self.time_data[-1])
            
        self.ax1.set_ylim(0, 1)
        self.ax1_twin.set_ylim(15, 75)
        
        # 更新狀態圖表
        state_data = [self.simulator.get_current_state() for _ in self.time_data]
        self.state_line.set_data(self.time_data, state_data)
        
        if len(self.time_data) > 1:
            self.ax2.set_xlim(self.time_data[0], self.time_data[-1])
        
        # 更新特徵圖表
        for feature, line in self.feature_lines.items():
            if self.feature_data[feature]:
                line.set_data(self.time_data, self.feature_data[feature])
                ax = line.axes
                if len(self.time_data) > 1:
                    ax.set_xlim(self.time_data[0], self.time_data[-1])
                if self.feature_data[feature]:
                    y_min = min(self.feature_data[feature])
                    y_max = max(self.feature_data[feature])
                    y_range = y_max - y_min
                    ax.set_ylim(y_min - y_range*0.1, y_max + y_range*0.1)
        
        # 更新相關性分析
        if len(self.h_data) >= 100:  # 至少100個數據點
            self.corr_ax.clear()
            self.corr_ax.scatter(self.h_data[-100:], self.pwm_data[-100:], alpha=0.6, s=10)
            self.corr_ax.set_xlabel('活躍度 H')
            self.corr_ax.set_ylabel('PWM輸出 (%)')
            self.corr_ax.set_title('H值與PWM相關性')
            
            # 計算相關係數
            correlation = np.corrcoef(self.h_data[-100:], self.pwm_data[-100:])[0, 1]
            self.corr_ax.text(0.05, 0.95, f'r = {correlation:.3f}', 
                            transform=self.corr_ax.transAxes, 
                            bbox=dict(boxstyle="round", facecolor='wheat', alpha=0.8))
        
        # 重繪畫布
        try:
            self.main_canvas.draw_idle()
            self.feature_canvas.draw_idle()
            self.system_canvas.draw_idle()
        except:
            pass  # 忽略繪圖錯誤
            
    # 菜單回調函數
    def open_config(self):
        """開啟配置文件"""
        filename = filedialog.askopenfilename(
            title="選擇配置文件",
            filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # 載入配置
                # TODO: 實現配置載入邏輯
                self.status_text.set(f"已載入配置: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("錯誤", f"載入配置失敗: {str(e)}")
                
    def save_config(self):
        """保存配置文件"""
        filename = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                # 保存當前參數配置
                config = {}
                for param, var in self.param_vars.items():
                    if not param.endswith('_label'):
                        config[param] = var.get()
                        
                # TODO: 實現配置保存邏輯
                self.status_text.set(f"已保存配置: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("錯誤", f"保存配置失敗: {str(e)}")
                
    def export_data(self):
        """匯出數據"""
        if not self.time_data:
            messagebox.showwarning("警告", "沒有數據可以匯出")
            return
            
        filename = filedialog.asksaveasfilename(
            title="匯出數據",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['時間', '活躍度H', 'PWM輸出', 'ME', 'RSI', 'POP', 'FLOW'])
                    
                    for i in range(len(self.time_data)):
                        row = [
                            self.time_data[i],
                            self.h_data[i],
                            self.pwm_data[i],
                            self.feature_data['ME'][i] if i < len(self.feature_data['ME']) else 0,
                            self.feature_data['RSI'][i] if i < len(self.feature_data['RSI']) else 0,
                            self.feature_data['POP'][i] if i < len(self.feature_data['POP']) else 0,
                            self.feature_data['FLOW'][i] if i < len(self.feature_data['FLOW']) else 0,
                        ]
                        writer.writerow(row)
                        
                self.status_text.set(f"數據已匯出: {os.path.basename(filename)}")
                messagebox.showinfo("完成", f"數據已成功匯出到:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("錯誤", f"匯出數據失敗: {str(e)}")
                
    def open_config_editor(self):
        """開啟配置編輯器"""
        ConfigEditor(self.root)
        
    def open_log_viewer(self):
        """開啟日誌查看器"""
        LogViewer(self.root)
        
    def test_camera(self):
        """測試相機"""
        messagebox.showinfo("相機測試", "相機測試功能\n\n在實際硬體模式下會開啟相機預覽視窗")
        
    def test_pwm(self):
        """測試PWM"""
        if not self.is_running:
            messagebox.showwarning("警告", "請先啟動系統")
            return
            
        # 執行PWM測試序列
        test_values = [20, 30, 50, 70, 45]
        def run_test(index=0):
            if index < len(test_values):
                self.simulator.set_manual_pwm(test_values[index])
                self.status_text.set(f"PWM測試: {test_values[index]}%")
                self.root.after(1000, lambda: run_test(index + 1))
            else:
                self.status_text.set("PWM測試完成")
                
        run_test()
        
    def show_help(self):
        """顯示幫助"""
        help_text = """
智能水產養殖自動餵料控制系統 - 使用說明

1. 系統控制：
   - 點擊「啟動系統」開始運行
   - 選擇「模擬模式」或「硬體模式」
   
2. 參數調整：
   - 使用滑桿即時調整系統參數
   - 參數會立即套用到運行中的系統
   
3. 手動控制：
   - 調整PWM滑桿進行手動控制
   - 點擊「手動餵食」執行3秒餵食
   
4. 圖表監控：
   - 主要圖表：顯示H值與PWM輸出
   - 特徵分析：顯示四種特徵值變化
   - 系統分析：顯示相關性與性能指標
   
5. 數據管理：
   - 「匯出數據」保存實驗數據
   - 「保存配置」儲存參數設定
   
6. 系統測試：
   - 「相機測試」檢查攝影模組
   - 「PWM測試」驗證輸出控制
"""
        messagebox.showinfo("使用說明", help_text)
        
    def show_about(self):
        """顯示關於"""
        about_text = """
智能水產養殖自動餵料控制系統 v1.0

基於 Jetson Nano 和 ROS2 的智能餵料系統
通過視覺分析魚群活躍度來自動調節餵料量

技術特點：
• CLAHE影像增強
• 四種特徵提取算法 (ME, RSI, POP, FLOW)
• PI控制器自動調節
• 實時監控與數據記錄

開發環境：
• Python 3.8+
• ROS2 Foxy
• OpenCV, NumPy, Matplotlib
• Tkinter GUI

版權所有 © 2025
"""
        messagebox.showinfo("關於", about_text)
        
    def on_closing(self):
        """程序關閉處理"""
        if self.is_running:
            if messagebox.askokcancel("確認", "系統正在運行，確定要退出嗎？"):
                self.stop_system()
                self.root.quit()
        else:
            self.root.quit()


def main():
    """主函數"""
    app = AquaFeederGUI()
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.root.mainloop()


if __name__ == "__main__":
    main()
