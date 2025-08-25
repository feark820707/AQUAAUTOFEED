#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Advanced Aqua Feeder GUI
Complete implementation with scrollable interface and parameter management
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import time
import csv
import os
from datetime import datetime
import json
import random
import cv2
from PIL import Image, ImageTk

# Set matplotlib backend to avoid display issues
import matplotlib
matplotlib.use('TkAgg')

class ScrollableFrame(ttk.Frame):
    """A scrollable frame widget"""
    
    def __init__(self, container):
        super().__init__(container)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack components
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


class SimpleSimulator:
    """Simple built-in simulator"""
    
    def __init__(self):
        self.h_value = 0.5
        self.pwm_output = 45
        self.features = {'ME': 0.3, 'RSI': 0.6, 'POP': 0.4, 'FLOW': 0.5}
        self.state = 'EVALUATION'
        self.last_update = time.time()
        
        # Parameters
        self.h_hi = 0.65
        self.h_lo = 0.35
        self.kp = 15.0
        self.ki = 2.0
        
    def get_current_state(self):
        # Simple state evolution
        dt = time.time() - self.last_update
        self.last_update = time.time()
        
        # Update features with some variation
        for feature in self.features:
            self.features[feature] += random.uniform(-0.02, 0.02)
            self.features[feature] = max(0, min(1, self.features[feature]))
            
        # Update H value using feature fusion
        self.h_value = (0.4 * self.features['RSI'] + 
                       0.3 * self.features['POP'] + 
                       0.2 * self.features['FLOW'] - 
                       0.1 * self.features['ME'])
        self.h_value = max(0, min(1, self.h_value))
        
        # Simple PI control
        if self.h_value > self.h_hi:
            target_pwm = 60
        elif self.h_value < self.h_lo:
            target_pwm = 30
        else:
            target_pwm = 45
            
        error = target_pwm - self.pwm_output
        self.pwm_output += self.kp * error * dt * 0.1
        self.pwm_output = max(20, min(70, self.pwm_output))
        
        return {
            'h_value': self.h_value,
            'pwm_output': self.pwm_output,
            'features': self.features.copy(),
            'state': self.state
        }
        
    def set_parameters(self, **kwargs):
        if 'h_hi' in kwargs:
            self.h_hi = kwargs['h_hi']
        if 'h_lo' in kwargs:
            self.h_lo = kwargs['h_lo']
        if 'kp' in kwargs:
            self.kp = kwargs['kp']
        if 'ki' in kwargs:
            self.ki = kwargs['ki']
            
    def manual_feed(self):
        self.h_value = min(1.0, self.h_value + 0.15)
        print("Manual feeding triggered")


class StandaloneAdvancedGUI:
    """Standalone Advanced GUI with all features"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        
        # System state
        self.is_running = False
        self.mode = "simulation"
        self.simulator = SimpleSimulator()
        
        # Camera functionality
        self.camera = None
        self.use_camera = False
        self.camera_frame = None
        self.camera_label = None
        
        # Data storage
        self.time_data = []
        self.h_data = []
        self.pwm_data = []
        self.feature_data = {'ME': [], 'RSI': [], 'POP': [], 'FLOW': []}
        
        # Complete parameter definitions
        self.parameters = {
            # Control parameters
            'h_hi': {'value': 0.65, 'min': 0.5, 'max': 0.8, 'step': 0.01, 'category': 'Control'},
            'h_lo': {'value': 0.35, 'min': 0.2, 'max': 0.5, 'step': 0.01, 'category': 'Control'},
            'kp': {'value': 15.0, 'min': 1.0, 'max': 50.0, 'step': 0.5, 'category': 'Control'},
            'ki': {'value': 2.0, 'min': 0.1, 'max': 20.0, 'step': 0.1, 'category': 'Control'},
            'kd': {'value': 0.5, 'min': 0.0, 'max': 5.0, 'step': 0.1, 'category': 'Control'},
            
            # Feature fusion weights
            'alpha': {'value': 0.4, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'Fusion'},
            'beta': {'value': 0.3, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'Fusion'},
            'gamma': {'value': 0.2, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'Fusion'},
            'delta': {'value': 0.1, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'Fusion'},
            
            # Timing parameters
            'feed_duration': {'value': 0.6, 'min': 0.1, 'max': 2.0, 'step': 0.1, 'category': 'Timing'},
            'eval_duration': {'value': 3.0, 'min': 1.0, 'max': 10.0, 'step': 0.5, 'category': 'Timing'},
            'stable_duration': {'value': 1.0, 'min': 0.5, 'max': 5.0, 'step': 0.1, 'category': 'Timing'},
            
            # PWM parameters
            'pwm_min': {'value': 20.0, 'min': 0.0, 'max': 50.0, 'step': 1.0, 'category': 'PWM'},
            'pwm_max': {'value': 70.0, 'min': 50.0, 'max': 100.0, 'step': 1.0, 'category': 'PWM'},
            'pwm_baseline': {'value': 45.0, 'min': 20.0, 'max': 60.0, 'step': 1.0, 'category': 'PWM'},
            
            # Environmental parameters
            'water_temp': {'value': 25.0, 'min': 15.0, 'max': 35.0, 'step': 0.5, 'category': 'Environment'},
            'ph_level': {'value': 7.0, 'min': 6.0, 'max': 8.5, 'step': 0.1, 'category': 'Environment'},
            'dissolved_oxygen': {'value': 8.0, 'min': 5.0, 'max': 12.0, 'step': 0.1, 'category': 'Environment'},
        }
        
        # GUI Variables
        self.param_vars = {}
        self.status_vars = {}
        self.data_vars = {}
        
        # Auto-tuning
        self.auto_tune_enabled = False
        
        # Create interface
        self.create_main_interface()
        self.initialize_variables()
        self.start_data_update()
        
        print("Standalone Advanced GUI initialized successfully")
        
    def setup_main_window(self):
        """Setup main window"""
        self.root.title("Advanced Aqua Feeder Control System v2.0 - Standalone")
        self.root.geometry("1800x1000")
        self.root.minsize(1400, 800)
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom styles
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Data.TLabel', font=('Consolas', 10, 'bold'))
        
    def create_main_interface(self):
        """Create main interface with scrollable layout"""
        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel with scrollable content
        left_container = ttk.Frame(main_paned, width=500)
        main_paned.add(left_container, weight=1)
        
        # Create scrollable frame
        self.left_scrollable = ScrollableFrame(left_container)
        self.left_scrollable.pack(fill=tk.BOTH, expand=True)
        
        # Right panel for charts
        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=2)
        
        # Create all sections
        self.create_control_section(self.left_scrollable.scrollable_frame)
        self.create_status_section(self.left_scrollable.scrollable_frame)
        self.create_camera_section(self.left_scrollable.scrollable_frame)
        self.create_data_section(self.left_scrollable.scrollable_frame)
        self.create_parameter_sections(self.left_scrollable.scrollable_frame)
        self.create_auto_tune_section(self.left_scrollable.scrollable_frame)
        self.create_manual_section(self.left_scrollable.scrollable_frame)
        
        # Charts
        self.create_chart_section(right_panel)
        
        # Status bar
        self.create_status_bar()
        
    def create_control_section(self, parent):
        """Create system control section"""
        control_frame = ttk.LabelFrame(parent, text="System Control", padding=10)
        control_frame.pack(fill=tk.X, pady=5)
        
        # Mode selection
        mode_frame = ttk.Frame(control_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="simulation")
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                 values=["simulation", "hardware"], state="readonly")
        mode_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(button_frame, text="Start System", command=self.start_system)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop System", 
                                  command=self.stop_system, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.emergency_btn = ttk.Button(button_frame, text="Emergency Stop", 
                                       command=self.emergency_stop)
        self.emergency_btn.pack(side=tk.RIGHT)
        
    def create_status_section(self, parent):
        """Create status display section"""
        status_frame = ttk.LabelFrame(parent, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_vars = {
            'system': tk.StringVar(value="Stopped"),
            'safety': tk.StringVar(value="Normal"),
            'mode': tk.StringVar(value="Simulation"),
            'auto_tune': tk.StringVar(value="Disabled")
        }
        
        for i, (label, var) in enumerate([
            ("System:", self.status_vars['system']),
            ("Safety:", self.status_vars['safety']),
            ("Mode:", self.status_vars['mode']),
            ("Auto-tune:", self.status_vars['auto_tune'])
        ]):
            ttk.Label(status_frame, text=label).grid(row=i//2, column=(i%2)*2, sticky='w', pady=1)
            ttk.Label(status_frame, textvariable=var).grid(row=i//2, column=(i%2)*2+1, 
                                                          sticky='w', padx=(10, 20), pady=1)
            
    def create_camera_section(self, parent):
        """Create camera display section"""
        camera_frame = ttk.LabelFrame(parent, text="Camera View", padding=10)
        camera_frame.pack(fill=tk.X, pady=5)
        
        # Camera display area
        self.camera_label = ttk.Label(camera_frame, text="Camera Not Active")
        self.camera_label.pack(pady=10)
        
        # Camera controls
        cam_control_frame = ttk.Frame(camera_frame)
        cam_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.camera_btn = ttk.Button(cam_control_frame, text="Start Camera", 
                                    command=self.toggle_camera)
        self.camera_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Camera mode selection
        self.camera_mode_var = tk.StringVar(value="simulation")
        camera_mode_combo = ttk.Combobox(cam_control_frame, textvariable=self.camera_mode_var,
                                        values=["simulation", "hardware"], state="readonly", width=10)
        camera_mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.camera_status = ttk.Label(cam_control_frame, text="Inactive")
        self.camera_status.pack(side=tk.RIGHT)
        
        # Initialize camera update thread
        self.start_camera_update()
            
    def create_data_section(self, parent):
        """Create real-time data section"""
        data_frame = ttk.LabelFrame(parent, text="Real-time Data", padding=10)
        data_frame.pack(fill=tk.X, pady=5)
        
        self.data_vars = {
            'h_value': tk.StringVar(value="0.500"),
            'pwm_output': tk.StringVar(value="45.0%"),
            'me': tk.StringVar(value="0.300"),
            'rsi': tk.StringVar(value="0.600"),
            'pop': tk.StringVar(value="0.400"),
            'flow': tk.StringVar(value="0.500"),
            'correlation': tk.StringVar(value="0.000"),
            'efficiency': tk.StringVar(value="85.5%")
        }
        
        data_items = [
            ("H Value:", self.data_vars['h_value'], 'blue'),
            ("PWM Output:", self.data_vars['pwm_output'], 'red'),
            ("ME Feature:", self.data_vars['me'], 'black'),
            ("RSI Feature:", self.data_vars['rsi'], 'black'),
            ("POP Feature:", self.data_vars['pop'], 'black'),
            ("FLOW Feature:", self.data_vars['flow'], 'black'),
            ("H-PWM Correlation:", self.data_vars['correlation'], 'purple'),
            ("System Efficiency:", self.data_vars['efficiency'], 'green')
        ]
        
        for i, (label, var, color) in enumerate(data_items):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(data_frame, text=label).grid(row=row, column=col, sticky='w', pady=1)
            data_label = ttk.Label(data_frame, textvariable=var, style='Data.TLabel')
            data_label.grid(row=row, column=col+1, sticky='e', padx=(5, 10), pady=1)
            
    def create_parameter_sections(self, parent):
        """Create categorized parameter sections"""
        param_container = ttk.LabelFrame(parent, text="Parameter Control", padding=10)
        param_container.pack(fill=tk.X, pady=5)
        
        # Create notebook for categories
        param_notebook = ttk.Notebook(param_container)
        param_notebook.pack(fill=tk.X, pady=5)
        
        # Group parameters by category
        categories = {}
        for param_name, param_info in self.parameters.items():
            category = param_info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((param_name, param_info))
            
        # Create tab for each category
        for category, params in categories.items():
            frame = ttk.Frame(param_notebook)
            param_notebook.add(frame, text=category)
            
            # Create scrollable frame for this category if many parameters
            if len(params) > 6:
                scrollable_frame = ScrollableFrame(frame)
                scrollable_frame.pack(fill=tk.BOTH, expand=True)
                param_parent = scrollable_frame.scrollable_frame
            else:
                param_parent = frame
                
            self.create_parameter_controls(param_parent, params)
            
    def create_parameter_controls(self, parent, params):
        """Create parameter control widgets"""
        for i, (param_name, param_info) in enumerate(params):
            # Parameter frame
            param_frame = ttk.Frame(parent)
            param_frame.pack(fill=tk.X, pady=3)
            
            # Label
            label_text = f"{param_name.replace('_', ' ').title()}:"
            ttk.Label(param_frame, text=label_text, width=18).pack(side=tk.LEFT)
            
            # Current value variable
            if param_name not in self.param_vars:
                self.param_vars[param_name] = tk.DoubleVar(value=param_info['value'])
                
            # Scale
            scale = ttk.Scale(param_frame,
                            from_=param_info['min'],
                            to=param_info['max'],
                            variable=self.param_vars[param_name],
                            orient='horizontal',
                            command=lambda val, name=param_name: self.on_parameter_change(name, val))
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Value display
            value_label = ttk.Label(param_frame, textvariable=self.param_vars[param_name], width=8)
            value_label.pack(side=tk.RIGHT)
            
            # Reset button for this parameter
            ttk.Button(param_frame, text="Reset", width=6,
                      command=lambda n=param_name, v=param_info['value']: self.reset_parameter(n, v)).pack(side=tk.RIGHT, padx=(5, 0))
                      
    def create_auto_tune_section(self, parent):
        """Create auto-tuning section"""
        auto_frame = ttk.LabelFrame(parent, text="Auto-Tuning", padding=10)
        auto_frame.pack(fill=tk.X, pady=5)
        
        # Auto-tune control
        auto_control_frame = ttk.Frame(auto_frame)
        auto_control_frame.pack(fill=tk.X, pady=5)
        
        self.auto_tune_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(auto_control_frame, text="Enable Auto-Tuning",
                                    variable=self.auto_tune_var, command=self.toggle_auto_tune)
        auto_check.pack(side=tk.LEFT)
        
        self.auto_status_label = ttk.Label(auto_control_frame, text="Disabled")
        self.auto_status_label.pack(side=tk.RIGHT)
        
        # Target correlation
        target_frame = ttk.Frame(auto_frame)
        target_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(target_frame, text="Target H-PWM Correlation:").pack(side=tk.LEFT)
        self.target_correlation_var = tk.DoubleVar(value=0.75)
        correlation_scale = ttk.Scale(target_frame, from_=0.5, to=0.95,
                                     variable=self.target_correlation_var, orient='horizontal')
        correlation_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        correlation_label = ttk.Label(target_frame, textvariable=self.target_correlation_var, width=6)
        correlation_label.pack(side=tk.RIGHT)
        
    def create_manual_section(self, parent):
        """Create manual control section"""
        manual_frame = ttk.LabelFrame(parent, text="Manual Controls", padding=10)
        manual_frame.pack(fill=tk.X, pady=5)
        
        # Manual PWM
        pwm_frame = ttk.Frame(manual_frame)
        pwm_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(pwm_frame, text="Manual PWM:").pack(side=tk.LEFT)
        self.manual_pwm_var = tk.DoubleVar(value=45.0)
        pwm_scale = ttk.Scale(pwm_frame, from_=0, to=100, variable=self.manual_pwm_var,
                             orient='horizontal', command=self.on_manual_pwm_change)
        pwm_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        pwm_label = ttk.Label(pwm_frame, textvariable=self.manual_pwm_var, width=6)
        pwm_label.pack(side=tk.RIGHT)
        
        # Action buttons
        button_frame = ttk.Frame(manual_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Manual Feed", command=self.manual_feed).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Reset All", command=self.reset_all_parameters).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Config", command=self.load_config).pack(side=tk.RIGHT)
        
    def create_chart_section(self, parent):
        """Create chart display section"""
        chart_frame = ttk.LabelFrame(parent, text="Data Visualization", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chart notebook
        chart_notebook = ttk.Notebook(chart_frame)
        chart_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main charts tab
        main_tab = ttk.Frame(chart_notebook)
        chart_notebook.add(main_tab, text="Main Monitor")
        self.create_main_charts(main_tab)
        
        # Feature charts tab
        feature_tab = ttk.Frame(chart_notebook)
        chart_notebook.add(feature_tab, text="Features")
        self.create_feature_charts(feature_tab)
        
        # Performance tab
        performance_tab = ttk.Frame(chart_notebook)
        chart_notebook.add(performance_tab, text="Performance")
        self.create_performance_charts(performance_tab)
        
    def create_main_charts(self, parent):
        """Create main monitoring charts"""
        self.main_fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.main_fig.suptitle('System Performance Monitor')
        
        self.ax1.set_title('H Value and Thresholds')
        self.ax1.set_ylabel('H Value')
        self.ax1.grid(True, alpha=0.3)
        
        self.ax2.set_title('PWM Output')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('PWM (%)')
        self.ax2.grid(True, alpha=0.3)
        
        self.main_canvas = FigureCanvasTkAgg(self.main_fig, parent)
        self.main_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_feature_charts(self, parent):
        """Create feature analysis charts"""
        self.feature_fig, self.feature_axes = plt.subplots(2, 2, figsize=(10, 8))
        self.feature_fig.suptitle('Feature Analysis')
        
        feature_names = ['ME', 'RSI', 'POP', 'FLOW']
        colors = ['blue', 'green', 'orange', 'purple']
        
        for ax, name, color in zip(self.feature_axes.flat, feature_names, colors):
            ax.set_title(f'{name} Feature')
            ax.set_ylabel(name)
            ax.grid(True, alpha=0.3)
            
        self.feature_canvas = FigureCanvasTkAgg(self.feature_fig, parent)
        self.feature_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_performance_charts(self, parent):
        """Create performance analysis charts"""
        self.perf_fig, ((self.perf_ax1, self.perf_ax2), 
                       (self.perf_ax3, self.perf_ax4)) = plt.subplots(2, 2, figsize=(10, 8))
        self.perf_fig.suptitle('Performance Analysis')
        
        self.perf_ax1.set_title('H-PWM Correlation')
        self.perf_ax2.set_title('Parameter Stability')
        self.perf_ax3.set_title('System Efficiency')
        self.perf_ax4.set_title('Response Time')
        
        for ax in [self.perf_ax1, self.perf_ax2, self.perf_ax3, self.perf_ax4]:
            ax.grid(True, alpha=0.3)
            
        self.perf_canvas = FigureCanvasTkAgg(self.perf_fig, parent)
        self.perf_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Label(self.root, text="Advanced System Ready - All features available",
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def initialize_variables(self):
        """Initialize all variables"""
        for param_name, param_info in self.parameters.items():
            if param_name not in self.param_vars:
                self.param_vars[param_name] = tk.DoubleVar(value=param_info['value'])
                
    # Event handlers
    def start_system(self):
        """Start the system"""
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_vars['system'].set("Running")
        
        # Apply parameters to simulator
        self.apply_parameters()
        
        print(f"System started in {self.mode} mode")
        self.update_status_bar("System started successfully")
        
    def stop_system(self):
        """Stop the system"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_vars['system'].set("Stopped")
        
        print("System stopped")
        self.update_status_bar("System stopped")
        
    def emergency_stop(self):
        """Emergency stop"""
        self.stop_system()
        self.status_vars['safety'].set("Emergency Stop")
        self.manual_pwm_var.set(0)
        
        print("EMERGENCY STOP ACTIVATED")
        self.update_status_bar("EMERGENCY STOP - System halted")
        
    def on_mode_change(self, event=None):
        """Handle mode change"""
        self.mode = self.mode_var.get()
        self.status_vars['mode'].set(self.mode.title())
        print(f"Mode changed to: {self.mode}")
        self.update_status_bar(f"Mode changed to {self.mode}")
        
    def on_parameter_change(self, param_name, value):
        """Handle parameter changes"""
        try:
            float_value = float(value)
            self.parameters[param_name]['value'] = float_value
            
            if self.is_running:
                self.apply_parameters()
                
            print(f"Parameter {param_name} = {float_value:.3f}")
            
        except ValueError:
            pass
            
    def apply_parameters(self):
        """Apply parameters to simulator"""
        params = {name: info['value'] for name, info in self.parameters.items()}
        self.simulator.set_parameters(**params)
        
    def reset_parameter(self, param_name, default_value):
        """Reset single parameter"""
        self.param_vars[param_name].set(default_value)
        self.on_parameter_change(param_name, default_value)
        
    def reset_all_parameters(self):
        """Reset all parameters"""
        for param_name, param_info in self.parameters.items():
            self.param_vars[param_name].set(param_info['value'])
            
        self.apply_parameters()
        print("All parameters reset")
        self.update_status_bar("All parameters reset to defaults")
        
    def toggle_auto_tune(self):
        """Toggle auto-tuning"""
        self.auto_tune_enabled = self.auto_tune_var.get()
        self.status_vars['auto_tune'].set("Active" if self.auto_tune_enabled else "Disabled")
        print(f"Auto-tuning {'enabled' if self.auto_tune_enabled else 'disabled'}")
        
    def on_manual_pwm_change(self, value):
        """Handle manual PWM change"""
        print(f"Manual PWM: {float(value):.1f}%")
        
    def manual_feed(self):
        """Manual feeding"""
        self.last_feed_time = time.time()  # Track feeding time for camera display
        self.simulator.manual_feed()
        self.update_status_bar("Manual feeding executed")
        
    def save_config(self):
        """Save configuration"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            
            if filename:
                config = {
                    'parameters': {name: var.get() for name, var in self.param_vars.items()},
                    'mode': self.mode,
                    'auto_tune': self.auto_tune_enabled,
                    'target_correlation': self.target_correlation_var.get()
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                print(f"Configuration saved to {filename}")
                self.update_status_bar("Configuration saved")
                
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            
    def load_config(self):
        """Load configuration"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)
                    
                # Load parameters
                for name, value in config.get('parameters', {}).items():
                    if name in self.param_vars:
                        self.param_vars[name].set(value)
                        
                # Load other settings
                if 'mode' in config:
                    self.mode_var.set(config['mode'])
                    self.on_mode_change()
                    
                if 'target_correlation' in config:
                    self.target_correlation_var.set(config['target_correlation'])
                    
                self.apply_parameters()
                print(f"Configuration loaded from {filename}")
                self.update_status_bar("Configuration loaded")
                
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
            
    def start_data_update(self):
        """Start data update loop"""
        def update_data():
            if self.is_running:
                # Get data from simulator
                state = self.simulator.get_current_state()
                
                # Update displays
                self.data_vars['h_value'].set(f"{state['h_value']:.3f}")
                self.data_vars['pwm_output'].set(f"{state['pwm_output']:.1f}%")
                
                features = state['features']
                self.data_vars['me'].set(f"{features['ME']:.3f}")
                self.data_vars['rsi'].set(f"{features['RSI']:.3f}")
                self.data_vars['pop'].set(f"{features['POP']:.3f}")
                self.data_vars['flow'].set(f"{features['FLOW']:.3f}")
                
                # Update data arrays
                current_time = time.time()
                if not hasattr(self, 'start_time'):
                    self.start_time = current_time
                    
                elapsed_time = current_time - self.start_time
                
                self.time_data.append(elapsed_time)
                self.h_data.append(state['h_value'])
                self.pwm_data.append(state['pwm_output'])
                
                for feature, value in features.items():
                    if feature in self.feature_data:
                        self.feature_data[feature].append(value)
                
                # Calculate performance metrics
                if len(self.h_data) > 10:
                    correlation = np.corrcoef(self.h_data[-50:], self.pwm_data[-50:])[0, 1]
                    self.data_vars['correlation'].set(f"{correlation:.3f}")
                    
                    # Simple efficiency calculation
                    h_variance = np.var(self.h_data[-20:])
                    efficiency = max(0, min(100, 100 * (1 - h_variance * 5)))
                    self.data_vars['efficiency'].set(f"{efficiency:.1f}%")
                
                # Keep data manageable
                max_points = 200
                if len(self.time_data) > max_points:
                    self.time_data = self.time_data[-max_points:]
                    self.h_data = self.h_data[-max_points:]
                    self.pwm_data = self.pwm_data[-max_points:]
                    for feature in self.feature_data:
                        self.feature_data[feature] = self.feature_data[feature][-max_points:]
                
                # Update charts
                self.update_charts()
                
            # Schedule next update
            self.root.after(100, update_data)
            
        # Start update loop
        self.root.after(100, update_data)
        
    def update_charts(self):
        """Update all charts"""
        if len(self.time_data) < 2:
            return
            
        try:
            # Update main charts
            self.ax1.clear()
            self.ax1.plot(self.time_data, self.h_data, 'b-', linewidth=2, label='H Value')
            self.ax1.axhline(y=self.param_vars['h_hi'].get(), color='r', 
                           linestyle='--', alpha=0.7, label='H_hi')
            self.ax1.axhline(y=self.param_vars['h_lo'].get(), color='g', 
                           linestyle='--', alpha=0.7, label='H_lo')
            self.ax1.set_title('H Value and Thresholds')
            self.ax1.set_ylabel('H Value')
            self.ax1.grid(True, alpha=0.3)
            self.ax1.legend()
            
            self.ax2.clear()
            self.ax2.plot(self.time_data, self.pwm_data, 'r-', linewidth=2, label='PWM Output')
            self.ax2.axhline(y=self.param_vars['pwm_baseline'].get(), color='orange', 
                           linestyle=':', alpha=0.7, label='Baseline')
            self.ax2.set_title('PWM Output')
            self.ax2.set_xlabel('Time (s)')
            self.ax2.set_ylabel('PWM (%)')
            self.ax2.grid(True, alpha=0.3)
            self.ax2.legend()
            
            self.main_canvas.draw()
            
            # Update feature charts
            colors = ['blue', 'green', 'orange', 'purple']
            feature_names = ['ME', 'RSI', 'POP', 'FLOW']
            
            for ax, name, color in zip(self.feature_axes.flat, feature_names, colors):
                ax.clear()
                if name in self.feature_data and len(self.feature_data[name]) > 0:
                    ax.plot(self.time_data, self.feature_data[name], 
                           color=color, linewidth=2, label=name)
                ax.set_title(f'{name} Feature')
                ax.set_ylabel(name)
                ax.grid(True, alpha=0.3)
                ax.legend()
                
            self.feature_axes[1, 0].set_xlabel('Time (s)')
            self.feature_axes[1, 1].set_xlabel('Time (s)')
            
            self.feature_canvas.draw()
            
            # Update performance charts
            if len(self.h_data) > 20:
                # H-PWM correlation over time
                correlations = []
                window_size = 20
                for i in range(window_size, len(self.h_data)):
                    corr = np.corrcoef(self.h_data[i-window_size:i], 
                                     self.pwm_data[i-window_size:i])[0, 1]
                    correlations.append(corr)
                    
                if correlations:
                    self.perf_ax1.clear()
                    self.perf_ax1.plot(self.time_data[window_size:], correlations, 
                                     'purple', linewidth=2, label='Correlation')
                    self.perf_ax1.axhline(y=self.target_correlation_var.get(), 
                                        color='red', linestyle='--', alpha=0.7, label='Target')
                    self.perf_ax1.set_title('H-PWM Correlation')
                    self.perf_ax1.set_ylabel('Correlation')
                    self.perf_ax1.grid(True, alpha=0.3)
                    self.perf_ax1.legend()
                    
            self.perf_canvas.draw()
            
        except Exception as e:
            print(f"Chart update error: {e}")
            
    def update_status_bar(self, message):
        """Update status bar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.config(text=f"[{timestamp}] {message}")
        
    # Camera functionality methods
    def toggle_camera(self):
        """Toggle camera on/off"""
        if not self.use_camera:
            self.start_camera()
        else:
            self.stop_camera()
            
    def start_camera(self):
        """Start camera capture"""
        try:
            camera_mode = self.camera_mode_var.get()
            if camera_mode == "hardware":
                self.camera = cv2.VideoCapture(0)
                if self.camera.isOpened():
                    self.use_camera = True
                    self.camera_btn.config(text="Stop Camera")
                    self.camera_status.config(text="Hardware Active")
                    print("Hardware camera started successfully")
                else:
                    raise Exception("Cannot open hardware camera")
            else:
                # Simulation mode
                self.use_camera = True
                self.camera_btn.config(text="Stop Camera")
                self.camera_status.config(text="Simulation Active")
                print("Camera simulation mode activated")
                
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            print(f"Camera error: {e}")
            
    def stop_camera(self):
        """Stop camera capture"""
        self.use_camera = False
        if self.camera:
            self.camera.release()
            self.camera = None
        self.camera_btn.config(text="Start Camera")
        self.camera_status.config(text="Inactive")
        self.camera_label.config(image='', text="Camera Not Active")
        print("Camera stopped")
        
    def start_camera_update(self):
        """Start camera update thread"""
        def update_camera():
            while True:
                if self.use_camera:
                    try:
                        camera_mode = self.camera_mode_var.get()
                        if camera_mode == "hardware" and self.camera:
                            ret, frame = self.camera.read()
                            if ret:
                                self.display_camera_frame(frame)
                        else:
                            # Generate simulation frame
                            frame = self.generate_simulation_frame()
                            self.display_camera_frame(frame)
                    except Exception as e:
                        print(f"Camera update error: {e}")
                time.sleep(0.033)  # ~30 FPS
                
        thread = threading.Thread(target=update_camera, daemon=True)
        thread.start()
        
    def generate_simulation_frame(self):
        """Generate simulated camera frame with fish behavior"""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:] = (20, 50, 100)  # Dark blue background for aquarium
        
        # Add some moving fish-like objects
        t = time.time()
        for i in range(5):
            # Fish movement patterns
            x = int(160 + 80 * np.sin(t * 0.5 + i * 1.2))
            y = int(120 + 60 * np.cos(t * 0.3 + i * 0.8))
            
            # Ensure fish stay within frame
            x = max(20, min(300, x))
            y = max(20, min(220, y))
            
            # Draw fish as ellipse
            cv2.ellipse(frame, (x, y), (12, 6), int(t * 30 + i * 60), 0, 360, (150, 200, 255), -1)
            
            # Add some bubbles
            if i < 3:
                bubble_x = int(50 + i * 100 + 20 * np.sin(t * 2 + i))
                bubble_y = int(200 - (t * 30 + i * 20) % 180)
                cv2.circle(frame, (bubble_x, bubble_y), 3, (200, 200, 200), 1)
        
        # Add system information overlay
        current_state = self.simulator.get_current_state()
        h_val = current_state['h_value']
        pwm_val = current_state['pwm_output']
        
        # Draw information text
        cv2.putText(frame, f"H: {h_val:.3f}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"PWM: {pwm_val:.1f}%", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"Mode: {self.mode}", (10, 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add feeding indicator
        if hasattr(self, 'last_feed_time'):
            if time.time() - self.last_feed_time < 2.0:
                cv2.putText(frame, "FEEDING", (200, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame
        
    def display_camera_frame(self, frame):
        """Display camera frame in GUI"""
        try:
            # Resize frame to fit display area
            frame_resized = cv2.resize(frame, (320, 240))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image and then to PhotoImage
            pil_image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image=pil_image)
            
            # Update label (must be done in main thread)
            self.root.after(0, lambda: self.camera_label.config(image=photo, text=''))
            self.root.after(0, lambda: setattr(self.camera_label, 'image', photo))
            
        except Exception as e:
            print(f"Display frame error: {e}")
        
    def run(self):
        """Run the application"""
        print("Starting Advanced Aqua Feeder GUI...")
        print("All features ready:")
        print("✓ Scrollable interface")
        print("✓ Complete parameter management") 
        print("✓ Real-time data visualization")
        print("✓ Auto-tuning capabilities")
        print("✓ Configuration save/load")
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = StandaloneAdvancedGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")


if __name__ == "__main__":
    main()
