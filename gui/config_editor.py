#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置編輯器 - 系統參數配置界面

提供友好的圖形界面來編輯系統配置文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml
import json
import os
from typing import Dict, Any


class ConfigEditor:
    """配置編輯器類"""
    
    def __init__(self, parent=None):
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.setup_window()
        
        # 配置數據
        self.config_data = {}
        self.config_file = None
        
        # 創建界面
        self.create_interface()
        self.load_default_config()
        
    def setup_window(self):
        """設置窗口"""
        self.window.title("系統配置編輯器")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
    def create_interface(self):
        """創建界面"""
        # 工具欄
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="載入配置", command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="另存為", command=self.save_as_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="重設為預設", command=self.reset_to_default).pack(side=tk.LEFT, padx=(0, 5))
        
        # 主要內容區
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 創建筆記本控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 各配置頁面
        self.create_hardware_config()
        self.create_control_config()
        self.create_vision_config()
        self.create_feature_config()
        self.create_validation_config()
        
        # 狀態欄
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        
    def create_hardware_config(self):
        """創建硬體配置頁面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="硬體配置")
        
        # 滾動框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # PWM配置
        pwm_group = ttk.LabelFrame(scrollable_frame, text="PWM控制器配置", padding=10)
        pwm_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(pwm_group, "hardware.pwm.pin", "PWM引腳", "18", int)
        self.create_config_entry(pwm_group, "hardware.pwm.frequency", "PWM頻率 (Hz)", "1000", int)
        self.create_config_entry(pwm_group, "hardware.pwm.min_duty_cycle", "最小占空比 (%)", "20", int)
        self.create_config_entry(pwm_group, "hardware.pwm.max_duty_cycle", "最大占空比 (%)", "70", int)
        
        # 相機配置
        camera_group = ttk.LabelFrame(scrollable_frame, text="相機配置", padding=10)
        camera_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(camera_group, "hardware.camera.device_id", "設備ID", "0", int)
        self.create_config_entry(camera_group, "hardware.camera.resolution", "解析度", "[1920, 1080]", str)
        self.create_config_entry(camera_group, "hardware.camera.fps", "幀率", "60", int)
        self.create_config_entry(camera_group, "hardware.camera.exposure", "曝光值", "-1", int)
        
        # GPIO配置
        gpio_group = ttk.LabelFrame(scrollable_frame, text="GPIO配置", padding=10)
        gpio_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(gpio_group, "hardware.gpio.led_pin", "LED引腳", "19", int)
        self.create_config_entry(gpio_group, "hardware.gpio.airflow_pins", "氣泡盤引腳", "[20, 21, 22]", str)
        
    def create_control_config(self):
        """創建控制配置頁面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="控制配置")
        
        # 滾動框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 時間參數
        timing_group = ttk.LabelFrame(scrollable_frame, text="時間參數", padding=10)
        timing_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(timing_group, "controller.timing.t_feed", "餵食時間 (秒)", "0.6", float)
        self.create_config_entry(timing_group, "controller.timing.t_eval", "評估時間 (秒)", "3.0", float)
        self.create_config_entry(timing_group, "controller.timing.t_settle", "穩定時間 (秒)", "1.0", float)
        
        # 門檻參數
        threshold_group = ttk.LabelFrame(scrollable_frame, text="門檻參數", padding=10)
        threshold_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(threshold_group, "controller.thresholds.H_hi", "高活躍門檻", "0.65", float)
        self.create_config_entry(threshold_group, "controller.thresholds.H_lo", "低活躍門檻", "0.35", float)
        
        # PI控制器參數
        pi_group = ttk.LabelFrame(scrollable_frame, text="PI控制器參數", padding=10)
        pi_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(pi_group, "controller.pi_controller.Kp", "比例增益", "15.0", float)
        self.create_config_entry(pi_group, "controller.pi_controller.Ki", "積分增益", "2.0", float)
        self.create_config_entry(pi_group, "controller.pi_controller.max_integral", "最大積分值", "10.0", float)
        
        # 約束參數
        constraint_group = ttk.LabelFrame(scrollable_frame, text="約束參數", padding=10)
        constraint_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(constraint_group, "controller.constraints.delta_up", "PWM上升限制", "10.0", float)
        self.create_config_entry(constraint_group, "controller.constraints.delta_down", "PWM下降限制", "15.0", float)
        
    def create_vision_config(self):
        """創建視覺配置頁面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="視覺配置")
        
        # 滾動框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 影像處理參數
        image_group = ttk.LabelFrame(scrollable_frame, text="影像處理參數", padding=10)
        image_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(image_group, "vision.clahe.clip_limit", "CLAHE裁剪限制", "2.0", float)
        self.create_config_entry(image_group, "vision.clahe.tile_grid_size", "CLAHE網格大小", "[8, 8]", str)
        self.create_config_entry(image_group, "vision.histogram_matching.enabled", "啟用直方圖匹配", "False", bool)
        
        # ROI配置
        roi_group = ttk.LabelFrame(scrollable_frame, text="ROI配置", padding=10)
        roi_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(roi_group, "vision.roi.roi_bub.x", "氣泡區域 X", "100", int)
        self.create_config_entry(roi_group, "vision.roi.roi_bub.y", "氣泡區域 Y", "100", int)
        self.create_config_entry(roi_group, "vision.roi.roi_bub.width", "氣泡區域寬度", "200", int)
        self.create_config_entry(roi_group, "vision.roi.roi_bub.height", "氣泡區域高度", "200", int)
        
        self.create_config_entry(roi_group, "vision.roi.roi_ring.x", "環形區域 X", "300", int)
        self.create_config_entry(roi_group, "vision.roi.roi_ring.y", "環形區域 Y", "200", int)
        self.create_config_entry(roi_group, "vision.roi.roi_ring.width", "環形區域寬度", "400", int)
        self.create_config_entry(roi_group, "vision.roi.roi_ring.height", "環形區域高度", "300", int)
        
    def create_feature_config(self):
        """創建特徵配置頁面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="特徵配置")
        
        # 滾動框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 特徵融合權重
        fusion_group = ttk.LabelFrame(scrollable_frame, text="特徵融合權重", padding=10)
        fusion_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(fusion_group, "feature_fusion.weights.alpha", "RSI權重 (α)", "0.4", float)
        self.create_config_entry(fusion_group, "feature_fusion.weights.beta", "POP權重 (β)", "0.3", float)
        self.create_config_entry(fusion_group, "feature_fusion.weights.gamma", "FLOW權重 (γ)", "0.2", float)
        self.create_config_entry(fusion_group, "feature_fusion.weights.delta", "ME權重 (δ)", "0.1", float)
        
        # 特徵正規化參數
        norm_group = ttk.LabelFrame(scrollable_frame, text="特徵正規化參數", padding=10)
        norm_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(norm_group, "feature_fusion.normalization.RSI_max", "RSI最大值", "1.0", float)
        self.create_config_entry(norm_group, "feature_fusion.normalization.POP_max", "POP最大值", "1.0", float)
        self.create_config_entry(norm_group, "feature_fusion.normalization.FLOW_max", "FLOW最大值", "1.0", float)
        self.create_config_entry(norm_group, "feature_fusion.normalization.ME_max", "ME最大值", "1.0", float)
        
        # 基準值
        baseline_group = ttk.LabelFrame(scrollable_frame, text="基準值", padding=10)
        baseline_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(baseline_group, "feature_fusion.baselines.RSI0", "RSI基準值", "0.3", float)
        self.create_config_entry(baseline_group, "feature_fusion.baselines.ME0", "ME基準值", "0.2", float)
        
    def create_validation_config(self):
        """創建驗證配置頁面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="驗證配置")
        
        # 滾動框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 驗證門檻
        threshold_group = ttk.LabelFrame(scrollable_frame, text="驗證門檻", padding=10)
        threshold_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(threshold_group, "validation.thresholds.min_correlation", "最小相關係數", "0.75", float)
        self.create_config_entry(threshold_group, "validation.thresholds.max_pwm_oscillation", "最大PWM振盪 (%)", "15.0", float)
        self.create_config_entry(threshold_group, "validation.thresholds.min_hit_rate", "最小命中率", "0.70", float)
        self.create_config_entry(threshold_group, "validation.thresholds.max_response_time", "最大反應時間 (秒)", "1.0", float)
        
        # 測試參數
        test_group = ttk.LabelFrame(scrollable_frame, text="測試參數", padding=10)
        test_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(test_group, "validation.test_params.oscillation_window", "振盪檢測窗口", "10.0", float)
        self.create_config_entry(test_group, "validation.test_params.disappear_min_time", "最小消失時間", "2.0", float)
        self.create_config_entry(test_group, "validation.test_params.disappear_max_time", "最大消失時間", "5.0", float)
        
        # 報告設定
        report_group = ttk.LabelFrame(scrollable_frame, text="報告設定", padding=10)
        report_group.pack(fill=tk.X, pady=(0, 10))
        
        self.create_config_entry(report_group, "validation.reporting.output_dir", "輸出目錄", "validation_results", str)
        self.create_config_entry(report_group, "validation.reporting.generate_plots", "生成圖表", "True", bool)
        self.create_config_entry(report_group, "validation.reporting.save_raw_data", "保存原始數據", "True", bool)
        
    def create_config_entry(self, parent, key, label, default_value, data_type):
        """創建配置輸入項"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        # 標籤
        ttk.Label(frame, text=f"{label}:", width=20).pack(side=tk.LEFT, padx=(0, 10))
        
        # 輸入框
        if data_type == bool:
            var = tk.BooleanVar(value=default_value == "True")
            entry = ttk.Checkbutton(frame, variable=var)
        else:
            var = tk.StringVar(value=str(default_value))
            entry = ttk.Entry(frame, textvariable=var, width=30)
            
        entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 存儲變數和類型信息
        if not hasattr(self, 'config_vars'):
            self.config_vars = {}
        self.config_vars[key] = (var, data_type)
        
        # 說明標籤
        ttk.Label(frame, text=f"({data_type.__name__})", foreground="gray").pack(side=tk.LEFT)
        
    def load_default_config(self):
        """載入預設配置"""
        default_config = {
            "hardware": {
                "pwm": {
                    "pin": 18,
                    "frequency": 1000,
                    "min_duty_cycle": 20,
                    "max_duty_cycle": 70
                },
                "camera": {
                    "device_id": 0,
                    "resolution": [1920, 1080],
                    "fps": 60,
                    "exposure": -1
                },
                "gpio": {
                    "led_pin": 19,
                    "airflow_pins": [20, 21, 22]
                }
            },
            "controller": {
                "timing": {
                    "t_feed": 0.6,
                    "t_eval": 3.0,
                    "t_settle": 1.0
                },
                "thresholds": {
                    "H_hi": 0.65,
                    "H_lo": 0.35
                },
                "pi_controller": {
                    "Kp": 15.0,
                    "Ki": 2.0,
                    "max_integral": 10.0
                },
                "constraints": {
                    "delta_up": 10.0,
                    "delta_down": 15.0
                }
            },
            "vision": {
                "clahe": {
                    "clip_limit": 2.0,
                    "tile_grid_size": [8, 8]
                },
                "histogram_matching": {
                    "enabled": False
                },
                "roi": {
                    "roi_bub": {"x": 100, "y": 100, "width": 200, "height": 200},
                    "roi_ring": {"x": 300, "y": 200, "width": 400, "height": 300}
                }
            },
            "feature_fusion": {
                "weights": {
                    "alpha": 0.4,
                    "beta": 0.3,
                    "gamma": 0.2,
                    "delta": 0.1
                },
                "normalization": {
                    "RSI_max": 1.0,
                    "POP_max": 1.0,
                    "FLOW_max": 1.0,
                    "ME_max": 1.0
                },
                "baselines": {
                    "RSI0": 0.3,
                    "ME0": 0.2
                }
            },
            "validation": {
                "thresholds": {
                    "min_correlation": 0.75,
                    "max_pwm_oscillation": 15.0,
                    "min_hit_rate": 0.70,
                    "max_response_time": 1.0
                },
                "test_params": {
                    "oscillation_window": 10.0,
                    "disappear_min_time": 2.0,
                    "disappear_max_time": 5.0
                },
                "reporting": {
                    "output_dir": "validation_results",
                    "generate_plots": True,
                    "save_raw_data": True
                }
            }
        }
        
        self.config_data = default_config
        self.update_interface_from_config()
        
    def update_interface_from_config(self):
        """從配置數據更新界面"""
        for key, (var, data_type) in self.config_vars.items():
            value = self.get_nested_value(self.config_data, key)
            if value is not None:
                if data_type == bool:
                    var.set(bool(value))
                else:
                    var.set(str(value))
                    
    def get_nested_value(self, data, key):
        """獲取嵌套字典的值"""
        keys = key.split('.')
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
        
    def set_nested_value(self, data, key, value):
        """設置嵌套字典的值"""
        keys = key.split('.')
        current = data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        
    def update_config_from_interface(self):
        """從界面更新配置數據"""
        for key, (var, data_type) in self.config_vars.items():
            try:
                if data_type == bool:
                    value = var.get()
                elif data_type == int:
                    value = int(var.get())
                elif data_type == float:
                    value = float(var.get())
                else:  # str
                    value_str = var.get().strip()
                    if value_str.startswith('[') and value_str.endswith(']'):
                        # 嘗試解析列表
                        try:
                            value = eval(value_str)
                        except:
                            value = value_str
                    else:
                        value = value_str
                        
                self.set_nested_value(self.config_data, key, value)
                
            except ValueError as e:
                messagebox.showerror("錯誤", f"參數 {key} 的值無效: {var.get()}")
                return False
                
        return True
        
    def load_config(self):
        """載入配置文件"""
        filename = filedialog.askopenfilename(
            title="載入配置文件",
            filetypes=[
                ("YAML files", "*.yaml *.yml"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    if filename.endswith('.json'):
                        self.config_data = json.load(f)
                    else:
                        self.config_data = yaml.safe_load(f)
                        
                self.config_file = filename
                self.update_interface_from_config()
                self.status_var.set(f"已載入: {os.path.basename(filename)}")
                
            except Exception as e:
                messagebox.showerror("錯誤", f"載入配置文件失敗:\n{str(e)}")
                
    def save_config(self):
        """保存配置文件"""
        if self.config_file:
            self.save_to_file(self.config_file)
        else:
            self.save_as_config()
            
    def save_as_config(self):
        """另存為配置文件"""
        filename = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".yaml",
            filetypes=[
                ("YAML files", "*.yaml *.yml"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.save_to_file(filename)
            self.config_file = filename
            
    def save_to_file(self, filename):
        """保存到文件"""
        if not self.update_config_from_interface():
            return
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                else:
                    yaml.safe_dump(self.config_data, f, default_flow_style=False, 
                                 allow_unicode=True, sort_keys=False)
                    
            self.status_var.set(f"已保存: {os.path.basename(filename)}")
            messagebox.showinfo("完成", f"配置已保存到:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"保存配置文件失敗:\n{str(e)}")
            
    def reset_to_default(self):
        """重設為預設值"""
        if messagebox.askyesno("確認", "確定要重設為預設配置嗎？\n所有修改將會遺失。"):
            self.load_default_config()
            self.status_var.set("已重設為預設配置")


if __name__ == "__main__":
    app = ConfigEditor()
    app.window.mainloop()
