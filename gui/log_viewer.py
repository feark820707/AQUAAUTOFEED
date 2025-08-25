#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日誌查看器 - 系統日誌和數據分析界面

提供系統運行日誌查看和數據分析功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import os
from datetime import datetime, timedelta
import csv


class LogViewer:
    """日誌查看器類"""
    
    def __init__(self, parent=None):
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.setup_window()
        
        # 數據
        self.log_data = None
        self.current_file = None
        
        # 創建界面
        self.create_interface()
        
    def setup_window(self):
        """設置窗口"""
        self.window.title("系統日誌查看器")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
    def create_interface(self):
        """創建界面"""
        # 工具欄
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="載入日誌", command=self.load_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="重新載入", command=self.reload_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="匯出分析", command=self.export_analysis).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="清除顯示", command=self.clear_display).pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔線
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # 時間範圍選擇
        ttk.Label(toolbar, text="時間範圍:").pack(side=tk.LEFT, padx=(0, 5))
        self.time_range_var = tk.StringVar(value="全部")
        time_range_combo = ttk.Combobox(
            toolbar, 
            textvariable=self.time_range_var,
            values=["全部", "最近1小時", "最近6小時", "最近24小時", "自定義"],
            state="readonly",
            width=12
        )
        time_range_combo.pack(side=tk.LEFT, padx=(0, 5))
        time_range_combo.bind('<<ComboboxSelected>>', self.on_time_range_change)
        
        # 主要內容區
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 分割面板
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左側面板：數據表格和統計
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # 右側面板：圖表分析
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        self.create_data_panel(left_frame)
        self.create_chart_panel(right_frame)
        
        # 狀態欄
        self.status_var = tk.StringVar(value="請載入日誌文件")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=5, pady=(0, 5))
        
    def create_data_panel(self, parent):
        """創建數據面板"""
        # 數據表格
        data_group = ttk.LabelFrame(parent, text="數據表格", padding=5)
        data_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 創建Treeview
        columns = ('時間', 'H值', 'PWM', '狀態', 'ME', 'RSI', 'POP', 'FLOW')
        self.tree = ttk.Treeview(data_group, columns=columns, show='headings', height=15)
        
        # 設置列寬
        column_widths = [120, 80, 60, 80, 80, 80, 80, 80]
        for i, (col, width) in enumerate(zip(columns, column_widths)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')
        
        # 滾動條
        v_scrollbar = ttk.Scrollbar(data_group, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(data_group, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 佈局
        self.tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # 統計信息
        stats_group = ttk.LabelFrame(parent, text="統計信息", padding=5)
        stats_group.pack(fill=tk.X)
        
        self.stats_text = tk.Text(stats_group, height=8, wrap=tk.WORD)
        stats_scrollbar = ttk.Scrollbar(stats_group, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True)
        stats_scrollbar.pack(side="right", fill="y")
        
    def create_chart_panel(self, parent):
        """創建圖表面板"""
        # 創建筆記本控件
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 時序圖表頁面
        timeseries_frame = ttk.Frame(notebook)
        notebook.add(timeseries_frame, text="時序分析")
        
        # 相關性分析頁面
        correlation_frame = ttk.Frame(notebook)
        notebook.add(correlation_frame, text="相關性分析")
        
        # 分布分析頁面
        distribution_frame = ttk.Frame(notebook)
        notebook.add(distribution_frame, text="分布分析")
        
        self.create_timeseries_chart(timeseries_frame)
        self.create_correlation_chart(correlation_frame)
        self.create_distribution_chart(distribution_frame)
        
    def create_timeseries_chart(self, parent):
        """創建時序圖表"""
        self.ts_fig, self.ts_axes = plt.subplots(3, 1, figsize=(10, 8))
        self.ts_fig.patch.set_facecolor('white')
        
        # H值和PWM圖表
        self.ts_axes[0].set_title('活躍度H與PWM輸出', fontweight='bold')
        self.ts_axes[0].set_ylabel('H值', color='blue')
        self.ts_axes[0].tick_params(axis='y', labelcolor='blue')
        
        # 創建雙Y軸
        self.ts_ax0_twin = self.ts_axes[0].twinx()
        self.ts_ax0_twin.set_ylabel('PWM (%)', color='red')
        self.ts_ax0_twin.tick_params(axis='y', labelcolor='red')
        
        # 特徵圖表
        self.ts_axes[1].set_title('特徵值變化', fontweight='bold')
        self.ts_axes[1].set_ylabel('特徵值')
        
        # 系統狀態圖表
        self.ts_axes[2].set_title('系統狀態', fontweight='bold')
        self.ts_axes[2].set_ylabel('狀態')
        self.ts_axes[2].set_xlabel('時間')
        
        self.ts_fig.tight_layout()
        
        # 嵌入tkinter
        self.ts_canvas = FigureCanvasTkAgg(self.ts_fig, parent)
        self.ts_canvas.draw()
        self.ts_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_correlation_chart(self, parent):
        """創建相關性圖表"""
        self.corr_fig, self.corr_axes = plt.subplots(2, 2, figsize=(10, 8))
        self.corr_fig.patch.set_facecolor('white')
        
        # H vs PWM散點圖
        self.corr_axes[0, 0].set_title('H值 vs PWM輸出')
        self.corr_axes[0, 0].set_xlabel('H值')
        self.corr_axes[0, 0].set_ylabel('PWM (%)')
        
        # 特徵相關性矩陣
        self.corr_axes[0, 1].set_title('特徵相關性矩陣')
        
        # H值與各特徵的相關性
        self.corr_axes[1, 0].set_title('H值與特徵相關性')
        self.corr_axes[1, 0].set_xlabel('特徵')
        self.corr_axes[1, 0].set_ylabel('相關係數')
        
        # PWM響應分析
        self.corr_axes[1, 1].set_title('PWM響應分析')
        self.corr_axes[1, 1].set_xlabel('時間 (秒)')
        self.corr_axes[1, 1].set_ylabel('PWM變化')
        
        self.corr_fig.tight_layout()
        
        # 嵌入tkinter
        self.corr_canvas = FigureCanvasTkAgg(self.corr_fig, parent)
        self.corr_canvas.draw()
        self.corr_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_distribution_chart(self, parent):
        """創建分布圖表"""
        self.dist_fig, self.dist_axes = plt.subplots(2, 2, figsize=(10, 8))
        self.dist_fig.patch.set_facecolor('white')
        
        # H值分布
        self.dist_axes[0, 0].set_title('H值分布')
        self.dist_axes[0, 0].set_xlabel('H值')
        self.dist_axes[0, 0].set_ylabel('頻率')
        
        # PWM分布
        self.dist_axes[0, 1].set_title('PWM分布')
        self.dist_axes[0, 1].set_xlabel('PWM (%)')
        self.dist_axes[0, 1].set_ylabel('頻率')
        
        # 狀態時間分布
        self.dist_axes[1, 0].set_title('狀態時間分布')
        self.dist_axes[1, 0].set_xlabel('狀態')
        self.dist_axes[1, 0].set_ylabel('時間 (秒)')
        
        # 特徵分布箱線圖
        self.dist_axes[1, 1].set_title('特徵分布')
        self.dist_axes[1, 1].set_xlabel('特徵')
        self.dist_axes[1, 1].set_ylabel('值')
        
        self.dist_fig.tight_layout()
        
        # 嵌入tkinter
        self.dist_canvas = FigureCanvasTkAgg(self.dist_fig, parent)
        self.dist_canvas.draw()
        self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def load_log(self):
        """載入日誌文件"""
        filename = filedialog.askopenfilename(
            title="選擇日誌文件",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                self.current_file = filename
                self.load_data_from_file(filename)
                
            except Exception as e:
                messagebox.showerror("錯誤", f"載入日誌文件失敗:\n{str(e)}")
                
    def load_data_from_file(self, filename):
        """從文件載入數據"""
        try:
            if filename.endswith('.csv'):
                # 嘗試不同的CSV格式
                try:
                    self.log_data = pd.read_csv(filename, encoding='utf-8')
                except:
                    try:
                        self.log_data = pd.read_csv(filename, encoding='utf-8-sig')
                    except:
                        self.log_data = pd.read_csv(filename, encoding='gbk')
                        
            elif filename.endswith(('.xlsx', '.xls')):
                self.log_data = pd.read_excel(filename)
            else:
                # 文本文件，嘗試解析
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # 簡單的文本解析邏輯
                data = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split()
                        if len(parts) >= 8:  # 假設至少有8個欄位
                            data.append(parts[:8])
                            
                if data:
                    columns = ['時間', 'H值', 'PWM', '狀態', 'ME', 'RSI', 'POP', 'FLOW']
                    self.log_data = pd.DataFrame(data, columns=columns)
                else:
                    raise ValueError("無法解析文本文件格式")
                    
            # 數據清理和轉換
            self.clean_and_convert_data()
            
            # 更新顯示
            self.update_display()
            
            self.status_var.set(f"已載入: {os.path.basename(filename)} ({len(self.log_data)} 筆記錄)")
            
        except Exception as e:
            raise Exception(f"數據載入失敗: {str(e)}")
            
    def clean_and_convert_data(self):
        """清理和轉換數據"""
        if self.log_data is None:
            return
            
        # 確保必要的欄位存在
        required_columns = ['時間', 'H值', 'PWM', '狀態', 'ME', 'RSI', 'POP', 'FLOW']
        
        # 如果欄位名稱不同，嘗試映射
        column_mapping = {
            'timestamp': '時間',
            'time': '時間',
            'H': 'H值',
            'activity': 'H值',
            'pwm': 'PWM',
            'pwm_output': 'PWM',
            'state': '狀態',
            'system_state': '狀態'
        }
        
        # 重命名欄位
        self.log_data.rename(columns=column_mapping, inplace=True)
        
        # 轉換數據類型
        try:
            # 轉換時間欄位
            if '時間' in self.log_data.columns:
                # 嘗試不同的時間格式
                try:
                    self.log_data['時間'] = pd.to_datetime(self.log_data['時間'])
                except:
                    # 如果是數字格式的時間戳
                    try:
                        self.log_data['時間'] = pd.to_numeric(self.log_data['時間'])
                        # 如果是相對時間，轉換為絕對時間
                        if self.log_data['時間'].max() < 1e6:  # 相對時間
                            start_time = datetime.now() - timedelta(seconds=self.log_data['時間'].max())
                            self.log_data['時間'] = start_time + pd.to_timedelta(self.log_data['時間'], unit='s')
                    except:
                        pass
                        
            # 轉換數值欄位
            numeric_columns = ['H值', 'PWM', 'ME', 'RSI', 'POP', 'FLOW']
            for col in numeric_columns:
                if col in self.log_data.columns:
                    self.log_data[col] = pd.to_numeric(self.log_data[col], errors='coerce')
                    
            # 移除無效數據
            self.log_data.dropna(subset=['H值', 'PWM'], inplace=True)
            
            # 重設索引
            self.log_data.reset_index(drop=True, inplace=True)
            
        except Exception as e:
            print(f"數據轉換警告: {str(e)}")
            
    def update_display(self):
        """更新顯示"""
        if self.log_data is None or self.log_data.empty:
            return
            
        # 應用時間範圍篩選
        filtered_data = self.apply_time_filter()
        
        # 更新表格
        self.update_table(filtered_data)
        
        # 更新統計信息
        self.update_statistics(filtered_data)
        
        # 更新圖表
        self.update_charts(filtered_data)
        
    def apply_time_filter(self):
        """應用時間範圍篩選"""
        if self.log_data is None or '時間' not in self.log_data.columns:
            return self.log_data
            
        time_range = self.time_range_var.get()
        
        if time_range == "全部":
            return self.log_data
            
        try:
            now = datetime.now()
            if time_range == "最近1小時":
                cutoff = now - timedelta(hours=1)
            elif time_range == "最近6小時":
                cutoff = now - timedelta(hours=6)
            elif time_range == "最近24小時":
                cutoff = now - timedelta(hours=24)
            else:
                return self.log_data
                
            # 篩選數據
            if pd.api.types.is_datetime64_any_dtype(self.log_data['時間']):
                return self.log_data[self.log_data['時間'] >= cutoff]
            else:
                return self.log_data
                
        except Exception:
            return self.log_data
            
    def update_table(self, data):
        """更新表格顯示"""
        # 清除現有數據
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if data is None or data.empty:
            return
            
        # 添加數據（最多顯示1000筆）
        display_data = data.tail(1000)
        
        for index, row in display_data.iterrows():
            values = []
            for col in ['時間', 'H值', 'PWM', '狀態', 'ME', 'RSI', 'POP', 'FLOW']:
                if col in row:
                    if col == '時間':
                        if pd.api.types.is_datetime64_any_dtype(data[col]):
                            values.append(row[col].strftime('%H:%M:%S'))
                        else:
                            values.append(f"{float(row[col]):.1f}s")
                    elif col == '狀態':
                        values.append(str(row[col]))
                    else:
                        try:
                            values.append(f"{float(row[col]):.3f}")
                        except:
                            values.append(str(row[col]))
                else:
                    values.append("N/A")
                    
            self.tree.insert('', 'end', values=values)
            
        # 滾動到底部
        if self.tree.get_children():
            self.tree.see(self.tree.get_children()[-1])
            
    def update_statistics(self, data):
        """更新統計信息"""
        self.stats_text.delete(1.0, tk.END)
        
        if data is None or data.empty:
            self.stats_text.insert(tk.END, "無數據")
            return
            
        try:
            stats = []
            stats.append(f"數據統計報告")
            stats.append("=" * 40)
            stats.append(f"總記錄數: {len(data)}")
            
            if '時間' in data.columns and len(data) > 1:
                if pd.api.types.is_datetime64_any_dtype(data['時間']):
                    duration = (data['時間'].iloc[-1] - data['時間'].iloc[0]).total_seconds()
                    stats.append(f"時間跨度: {duration:.1f} 秒")
                    
            # H值統計
            if 'H值' in data.columns:
                h_values = data['H值'].dropna()
                if not h_values.empty:
                    stats.append(f"\nH值統計:")
                    stats.append(f"  平均值: {h_values.mean():.3f}")
                    stats.append(f"  標準差: {h_values.std():.3f}")
                    stats.append(f"  最小值: {h_values.min():.3f}")
                    stats.append(f"  最大值: {h_values.max():.3f}")
                    
            # PWM統計
            if 'PWM' in data.columns:
                pwm_values = data['PWM'].dropna()
                if not pwm_values.empty:
                    stats.append(f"\nPWM統計:")
                    stats.append(f"  平均值: {pwm_values.mean():.1f}%")
                    stats.append(f"  標準差: {pwm_values.std():.1f}%")
                    stats.append(f"  最小值: {pwm_values.min():.1f}%")
                    stats.append(f"  最大值: {pwm_values.max():.1f}%")
                    
            # 相關性分析
            if 'H值' in data.columns and 'PWM' in data.columns:
                h_values = data['H值'].dropna()
                pwm_values = data['PWM'].dropna()
                if len(h_values) > 1 and len(pwm_values) > 1:
                    # 確保長度一致
                    min_len = min(len(h_values), len(pwm_values))
                    correlation = np.corrcoef(h_values[:min_len], pwm_values[:min_len])[0, 1]
                    stats.append(f"\n相關性分析:")
                    stats.append(f"  H值與PWM相關係數: {correlation:.3f}")
                    
                    if correlation >= 0.75:
                        stats.append(f"  ✓ 相關性良好 (≥0.75)")
                    else:
                        stats.append(f"  ✗ 相關性不足 (<0.75)")
                        
            # 狀態統計
            if '狀態' in data.columns:
                state_counts = data['狀態'].value_counts()
                if not state_counts.empty:
                    stats.append(f"\n狀態分布:")
                    for state, count in state_counts.items():
                        percentage = (count / len(data)) * 100
                        stats.append(f"  {state}: {count} ({percentage:.1f}%)")
                        
            self.stats_text.insert(tk.END, "\n".join(stats))
            
        except Exception as e:
            self.stats_text.insert(tk.END, f"統計計算錯誤: {str(e)}")
            
    def update_charts(self, data):
        """更新圖表"""
        if data is None or data.empty:
            return
            
        try:
            self.update_timeseries_chart(data)
            self.update_correlation_chart(data)
            self.update_distribution_chart(data)
            
        except Exception as e:
            print(f"圖表更新錯誤: {str(e)}")
            
    def update_timeseries_chart(self, data):
        """更新時序圖表"""
        # 清除現有圖表
        for ax in self.ts_axes:
            ax.clear()
        self.ts_ax0_twin.clear()
        
        if '時間' not in data.columns:
            # 使用索引作為時間軸
            x_data = data.index
            x_label = '記錄序號'
        else:
            x_data = data['時間']
            x_label = '時間'
            
        # H值和PWM圖表
        if 'H值' in data.columns:
            self.ts_axes[0].plot(x_data, data['H值'], 'b-', label='H值', alpha=0.8)
            self.ts_axes[0].set_ylabel('H值', color='blue')
            self.ts_axes[0].tick_params(axis='y', labelcolor='blue')
            
        if 'PWM' in data.columns:
            self.ts_ax0_twin.plot(x_data, data['PWM'], 'r-', label='PWM', alpha=0.8)
            self.ts_ax0_twin.set_ylabel('PWM (%)', color='red')
            self.ts_ax0_twin.tick_params(axis='y', labelcolor='red')
            
        self.ts_axes[0].set_title('活躍度H與PWM輸出')
        self.ts_axes[0].grid(True, alpha=0.3)
        
        # 特徵圖表
        feature_columns = ['ME', 'RSI', 'POP', 'FLOW']
        colors = ['green', 'orange', 'purple', 'brown']
        
        for i, (feature, color) in enumerate(zip(feature_columns, colors)):
            if feature in data.columns:
                self.ts_axes[1].plot(x_data, data[feature], color=color, label=feature, alpha=0.8)
                
        self.ts_axes[1].set_title('特徵值變化')
        self.ts_axes[1].set_ylabel('特徵值')
        self.ts_axes[1].legend()
        self.ts_axes[1].grid(True, alpha=0.3)
        
        # 系統狀態圖表
        if '狀態' in data.columns:
            # 將狀態轉換為數值
            state_mapping = {'停止': 0, '餵食': 1, '評估': 2, '穩定': 3}
            numeric_states = data['狀態'].map(state_mapping).fillna(0)
            
            self.ts_axes[2].plot(x_data, numeric_states, 'g-', marker='o', markersize=3, alpha=0.8)
            self.ts_axes[2].set_ylabel('狀態')
            self.ts_axes[2].set_yticks([0, 1, 2, 3])
            self.ts_axes[2].set_yticklabels(['停止', '餵食', '評估', '穩定'])
            
        self.ts_axes[2].set_title('系統狀態')
        self.ts_axes[2].set_xlabel(x_label)
        self.ts_axes[2].grid(True, alpha=0.3)
        
        self.ts_fig.tight_layout()
        self.ts_canvas.draw()
        
    def update_correlation_chart(self, data):
        """更新相關性圖表"""
        # 清除現有圖表
        for ax in self.corr_axes.flat:
            ax.clear()
            
        # H vs PWM散點圖
        if 'H值' in data.columns and 'PWM' in data.columns:
            h_values = data['H值'].dropna()
            pwm_values = data['PWM'].dropna()
            min_len = min(len(h_values), len(pwm_values))
            
            if min_len > 0:
                self.corr_axes[0, 0].scatter(h_values[:min_len], pwm_values[:min_len], alpha=0.6, s=20)
                self.corr_axes[0, 0].set_xlabel('H值')
                self.corr_axes[0, 0].set_ylabel('PWM (%)')
                self.corr_axes[0, 0].set_title('H值 vs PWM輸出')
                
                # 添加趨勢線
                try:
                    z = np.polyfit(h_values[:min_len], pwm_values[:min_len], 1)
                    p = np.poly1d(z)
                    self.corr_axes[0, 0].plot(h_values[:min_len], p(h_values[:min_len]), "r--", alpha=0.8)
                    
                    # 計算相關係數
                    correlation = np.corrcoef(h_values[:min_len], pwm_values[:min_len])[0, 1]
                    self.corr_axes[0, 0].text(0.05, 0.95, f'r = {correlation:.3f}', 
                                            transform=self.corr_axes[0, 0].transAxes,
                                            bbox=dict(boxstyle="round", facecolor='wheat'))
                except:
                    pass
                    
        # 特徵相關性矩陣
        numeric_columns = ['H值', 'PWM', 'ME', 'RSI', 'POP', 'FLOW']
        available_columns = [col for col in numeric_columns if col in data.columns]
        
        if len(available_columns) >= 2:
            corr_matrix = data[available_columns].corr()
            im = self.corr_axes[0, 1].imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
            
            # 設置標籤
            self.corr_axes[0, 1].set_xticks(range(len(available_columns)))
            self.corr_axes[0, 1].set_yticks(range(len(available_columns)))
            self.corr_axes[0, 1].set_xticklabels(available_columns, rotation=45)
            self.corr_axes[0, 1].set_yticklabels(available_columns)
            
            # 添加數值標籤
            for i in range(len(available_columns)):
                for j in range(len(available_columns)):
                    text = self.corr_axes[0, 1].text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                                   ha="center", va="center", color="black")
                                                   
            self.corr_axes[0, 1].set_title('特徵相關性矩陣')
            
        self.corr_fig.tight_layout()
        self.corr_canvas.draw()
        
    def update_distribution_chart(self, data):
        """更新分布圖表"""
        # 清除現有圖表
        for ax in self.dist_axes.flat:
            ax.clear()
            
        # H值分布
        if 'H值' in data.columns:
            h_values = data['H值'].dropna()
            if not h_values.empty:
                self.dist_axes[0, 0].hist(h_values, bins=30, alpha=0.7, color='blue', edgecolor='black')
                self.dist_axes[0, 0].set_xlabel('H值')
                self.dist_axes[0, 0].set_ylabel('頻率')
                self.dist_axes[0, 0].set_title('H值分布')
                
        # PWM分布
        if 'PWM' in data.columns:
            pwm_values = data['PWM'].dropna()
            if not pwm_values.empty:
                self.dist_axes[0, 1].hist(pwm_values, bins=30, alpha=0.7, color='red', edgecolor='black')
                self.dist_axes[0, 1].set_xlabel('PWM (%)')
                self.dist_axes[0, 1].set_ylabel('頻率')
                self.dist_axes[0, 1].set_title('PWM分布')
                
        # 特徵分布箱線圖
        feature_columns = ['ME', 'RSI', 'POP', 'FLOW']
        available_features = [col for col in feature_columns if col in data.columns]
        
        if available_features:
            feature_data = [data[col].dropna() for col in available_features]
            if any(len(d) > 0 for d in feature_data):
                self.dist_axes[1, 1].boxplot(feature_data, labels=available_features)
                self.dist_axes[1, 1].set_xlabel('特徵')
                self.dist_axes[1, 1].set_ylabel('值')
                self.dist_axes[1, 1].set_title('特徵分布')
                
        self.dist_fig.tight_layout()
        self.dist_canvas.draw()
        
    def on_time_range_change(self, event):
        """時間範圍變更回調"""
        self.update_display()
        
    def reload_log(self):
        """重新載入日誌"""
        if self.current_file:
            try:
                self.load_data_from_file(self.current_file)
            except Exception as e:
                messagebox.showerror("錯誤", f"重新載入失敗:\n{str(e)}")
        else:
            messagebox.showwarning("警告", "沒有已載入的文件")
            
    def export_analysis(self):
        """匯出分析報告"""
        if self.log_data is None:
            messagebox.showwarning("警告", "沒有數據可以匯出")
            return
            
        filename = filedialog.asksaveasfilename(
            title="匯出分析報告",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("系統日誌分析報告\n")
                    f.write("=" * 50 + "\n\n")
                    
                    # 獲取統計信息
                    stats_content = self.stats_text.get(1.0, tk.END)
                    f.write(stats_content)
                    
                self.status_var.set(f"分析報告已匯出: {os.path.basename(filename)}")
                messagebox.showinfo("完成", f"分析報告已匯出到:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("錯誤", f"匯出失敗:\n{str(e)}")
                
    def clear_display(self):
        """清除顯示"""
        # 清除表格
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 清除統計信息
        self.stats_text.delete(1.0, tk.END)
        
        # 清除圖表
        for ax in self.ts_axes:
            ax.clear()
        self.ts_ax0_twin.clear()
        
        for ax in self.corr_axes.flat:
            ax.clear()
            
        for ax in self.dist_axes.flat:
            ax.clear()
            
        # 重繪畫布
        self.ts_canvas.draw()
        self.corr_canvas.draw()
        self.dist_canvas.draw()
        
        self.log_data = None
        self.current_file = None
        self.status_var.set("顯示已清除")


if __name__ == "__main__":
    app = LogViewer()
    app.window.mainloop()
