#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Aqua Feeder GUI with Scrollable Interface
Enhanced parameter management for both simulation and hardware modes
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

# Import system modules
try:
    from gui.enhanced_simulator import EnhancedSystemSimulator
    from gui.config_editor import ConfigEditor
    from gui.log_viewer import LogViewer
except ImportError:
    # Mock fallbacks
    class EnhancedSystemSimulator:
        def __init__(self):
            self.h_value = 0.5
            self.pwm_output = 45
            self.features = {'ME': 0.3, 'RSI': 0.6, 'POP': 0.4, 'FLOW': 0.5}
            self.frame_width = 640
            self.frame_height = 480
            self.current_frame = None
            self.simulation_running = True
            
        def get_current_state(self):
            # Add some variation to simulate real data
            import random
            return {
                'h_value': max(0, min(1, self.h_value + random.uniform(-0.02, 0.02))),
                'pwm_output': max(20, min(70, self.pwm_output + random.uniform(-2, 2))),
                'features': {k: max(0, min(1, v + random.uniform(-0.05, 0.05))) 
                           for k, v in self.features.items()},
                'state': random.choice(['FEEDING', 'EVALUATION', 'STABLE'])
            }
            
        def get_camera_frame(self):
            import numpy as np
            import cv2
            
            # Generate a simple simulation frame
            frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
            frame[:] = (40, 80, 120)  # Water color
            
            # Add some moving circles to simulate fish
            import time
            t = time.time()
            for i in range(3):
                x = int(self.frame_width//2 + 100 * np.sin(t + i * 2))
                y = int(self.frame_height//2 + 80 * np.cos(t * 0.7 + i))
                cv2.circle(frame, (x, y), 15, (100, 150, 200), -1)
                
            # Add overlay info
            cv2.putText(frame, f"H: {self.h_value:.3f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"PWM: {self.pwm_output:.1f}%", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                       
            return frame
            
        def set_parameters(self, **kwargs):
            # Update internal parameters based on input
            if 'h_hi' in kwargs or 'h_lo' in kwargs or 'kp' in kwargs or 'ki' in kwargs:
                print(f"Simulator parameters updated: {list(kwargs.keys())}")
            
        def manual_feed(self):
            print("Manual feeding triggered in simulator")
            self.h_value = min(1.0, self.h_value + 0.1)
    
    ConfigEditor = None
    LogViewer = None


class ScrollableFrame(ttk.Frame):
    """A scrollable frame widget for GUI components that need more space"""
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
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
        
        # Bind mousewheel to canvas
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)
        self.canvas.bind('<Button-5>', self._on_mousewheel)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.delta:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


class AdvancedAquaFeederGUI:
    """Advanced GUI with scrollable interface and enhanced parameter management"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        
        # System state
        self.is_running = False
        self.mode = "simulation"
        self.simulator = EnhancedSystemSimulator()
        
        # Camera related
        self.camera = None
        self.use_camera = False
        
        # Data storage
        self.time_data = []
        self.h_data = []
        self.pwm_data = []
        self.feature_data = {'ME': [], 'RSI': [], 'POP': [], 'FLOW': []}
        
        # Parameter management
        self.parameters = {
            # Control parameters
            'h_hi': {'value': 0.65, 'min': 0.5, 'max': 0.8, 'step': 0.01, 'category': 'control'},
            'h_lo': {'value': 0.35, 'min': 0.2, 'max': 0.5, 'step': 0.01, 'category': 'control'},
            'kp': {'value': 15.0, 'min': 1.0, 'max': 50.0, 'step': 0.5, 'category': 'control'},
            'ki': {'value': 2.0, 'min': 0.1, 'max': 20.0, 'step': 0.1, 'category': 'control'},
            'kd': {'value': 0.5, 'min': 0.0, 'max': 5.0, 'step': 0.1, 'category': 'control'},
            
            # Feature fusion weights
            'alpha': {'value': 0.4, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'fusion'},
            'beta': {'value': 0.3, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'fusion'},
            'gamma': {'value': 0.2, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'fusion'},
            'delta': {'value': 0.1, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'category': 'fusion'},
            
            # Timing parameters
            'feed_duration': {'value': 0.6, 'min': 0.1, 'max': 2.0, 'step': 0.1, 'category': 'timing'},
            'eval_duration': {'value': 3.0, 'min': 1.0, 'max': 10.0, 'step': 0.5, 'category': 'timing'},
            'stable_duration': {'value': 1.0, 'min': 0.5, 'max': 5.0, 'step': 0.1, 'category': 'timing'},
            
            # PWM parameters
            'pwm_min': {'value': 20.0, 'min': 0.0, 'max': 50.0, 'step': 1.0, 'category': 'pwm'},
            'pwm_max': {'value': 70.0, 'min': 50.0, 'max': 100.0, 'step': 1.0, 'category': 'pwm'},
            'pwm_baseline': {'value': 45.0, 'min': 20.0, 'max': 60.0, 'step': 1.0, 'category': 'pwm'},
            
            # Camera parameters
            'camera_fps': {'value': 30, 'min': 10, 'max': 60, 'step': 5, 'category': 'camera'},
            'frame_width': {'value': 640, 'min': 320, 'max': 1920, 'step': 160, 'category': 'camera'},
            'frame_height': {'value': 480, 'min': 240, 'max': 1080, 'step': 120, 'category': 'camera'},
        }
        
        # GUI Variables
        self.param_vars = {}
        self.status_vars = {}
        self.data_vars = {}
        
        # Auto-adjustment settings
        self.auto_tune_enabled = False
        self.auto_tune_params = ['kp', 'ki', 'h_hi', 'h_lo']
        
        # Create interface
        self.create_main_interface()
        self.initialize_variables()
        
        # Start update loops
        self.start_data_update()
        self.start_camera_update()
        
        print("Advanced Aqua Feeder GUI initialized with scrollable interface")
        
    def setup_main_window(self):
        """Setup main window with optimized layout"""
        self.root.title("Advanced Aqua Feeder Control System v2.0")
        self.root.geometry("1800x1000")
        self.root.minsize(1400, 800)
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom styles
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Data.TLabel', font=('Consolas', 10, 'bold'))
        style.configure('Status.TLabel', font=('Consolas', 9))
        style.configure('Category.TLabel', font=('Arial', 9, 'bold'), foreground='blue')
        
    def create_main_interface(self):
        """Create main interface with scrollable components"""
        # Create main paned window for resizable layout
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel with scrollable content
        left_panel_container = ttk.Frame(main_paned, width=450)
        main_paned.add(left_panel_container, weight=1)
        
        # Create scrollable frame for left panel
        self.left_scrollable = ScrollableFrame(left_panel_container)
        self.left_scrollable.pack(fill=tk.BOTH, expand=True)
        
        # Right panel for charts
        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=2)
        
        # Create components in scrollable frame
        self.create_control_section(self.left_scrollable.scrollable_frame)
        self.create_mode_config_section(self.left_scrollable.scrollable_frame)
        self.create_camera_section(self.left_scrollable.scrollable_frame)
        self.create_data_section(self.left_scrollable.scrollable_frame)
        self.create_parameter_sections(self.left_scrollable.scrollable_frame)
        self.create_auto_tune_section(self.left_scrollable.scrollable_frame)
        self.create_manual_control_section(self.left_scrollable.scrollable_frame)
        
        # Create chart section in right panel
        self.create_chart_section(right_panel)
        
        # Create status bar
        self.create_status_bar()
        
    def create_control_section(self, parent):
        """Create main system control section"""
        control_frame = ttk.LabelFrame(parent, text="System Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Mode selection
        mode_frame = ttk.Frame(control_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Operation Mode:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="simulation")
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                 values=["simulation", "hardware"], state="readonly", width=12)
        mode_combo.pack(side=tk.RIGHT)
        mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(button_frame, text="Start System",
                                   command=self.start_system)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop System",
                                  command=self.stop_system, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.emergency_btn = ttk.Button(button_frame, text="Emergency Stop",
                                       command=self.emergency_stop)
        self.emergency_btn.pack(side=tk.RIGHT)
        
        # System status indicators
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create status variables
        self.status_vars = {
            'system': tk.StringVar(value="Stopped"),
            'camera': tk.StringVar(value="Disconnected"),
            'pwm': tk.StringVar(value="Not Initialized"),
            'safety': tk.StringVar(value="Normal")
        }
        
        # Status display grid
        for i, (label, var) in enumerate([
            ("System Status:", self.status_vars['system']),
            ("Camera Status:", self.status_vars['camera']),
            ("PWM Status:", self.status_vars['pwm']),
            ("Safety Status:", self.status_vars['safety'])
        ]):
            ttk.Label(status_frame, text=label).grid(row=i, column=0, sticky='w', pady=1)
            status_label = ttk.Label(status_frame, textvariable=var, style='Status.TLabel')
            status_label.grid(row=i, column=1, sticky='w', padx=(10, 0), pady=1)
            
    def create_mode_config_section(self, parent):
        """Create mode-specific configuration section"""
        config_frame = ttk.LabelFrame(parent, text="Mode Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=5)
        
        # Create notebook for different configuration tabs
        config_notebook = ttk.Notebook(config_frame)
        config_notebook.pack(fill=tk.X, pady=5)
        
        # Simulation mode config
        sim_frame = ttk.Frame(config_notebook)
        config_notebook.add(sim_frame, text="Simulation")
        
        ttk.Label(sim_frame, text="Fish Count:").grid(row=0, column=0, sticky='w', pady=2)
        self.fish_count_var = tk.IntVar(value=5)
        fish_scale = ttk.Scale(sim_frame, from_=1, to=10, variable=self.fish_count_var, orient='horizontal')
        fish_scale.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=2)
        
        ttk.Label(sim_frame, text="Environment Noise:").grid(row=1, column=0, sticky='w', pady=2)
        self.noise_var = tk.DoubleVar(value=0.1)
        noise_scale = ttk.Scale(sim_frame, from_=0.0, to=0.5, variable=self.noise_var, orient='horizontal')
        noise_scale.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=2)
        
        sim_frame.columnconfigure(1, weight=1)
        
        # Hardware mode config
        hw_frame = ttk.Frame(config_notebook)
        config_notebook.add(hw_frame, text="Hardware")
        
        ttk.Label(hw_frame, text="Camera Device:").grid(row=0, column=0, sticky='w', pady=2)
        self.camera_device_var = tk.IntVar(value=0)
        camera_combo = ttk.Combobox(hw_frame, textvariable=self.camera_device_var,
                                   values=[0, 1, 2], state="readonly", width=10)
        camera_combo.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=2)
        
        ttk.Label(hw_frame, text="PWM Frequency (Hz):").grid(row=1, column=0, sticky='w', pady=2)
        self.pwm_freq_var = tk.IntVar(value=1000)
        pwm_freq_entry = ttk.Entry(hw_frame, textvariable=self.pwm_freq_var, width=10)
        pwm_freq_entry.grid(row=1, column=1, sticky='w', padx=(10, 0), pady=2)
        
        ttk.Label(hw_frame, text="GPIO Pin:").grid(row=2, column=0, sticky='w', pady=2)
        self.gpio_pin_var = tk.IntVar(value=18)
        gpio_entry = ttk.Entry(hw_frame, textvariable=self.gpio_pin_var, width=10)
        gpio_entry.grid(row=2, column=1, sticky='w', padx=(10, 0), pady=2)
        
    def create_camera_section(self, parent):
        """Create camera display section"""
        camera_frame = ttk.LabelFrame(parent, text="Camera Monitor", padding=10)
        camera_frame.pack(fill=tk.X, pady=5)
        
        # Camera display area (smaller for scrollable layout)
        self.camera_label = ttk.Label(camera_frame, text="Camera Not Active",
                                     background='black', foreground='white')
        self.camera_label.pack(pady=10)
        
        # Camera controls
        cam_control_frame = ttk.Frame(camera_frame)
        cam_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.camera_btn = ttk.Button(cam_control_frame, text="Start Camera",
                                    command=self.toggle_camera)
        self.camera_btn.pack(side=tk.LEFT)
        
        self.record_btn = ttk.Button(cam_control_frame, text="Record",
                                    command=self.toggle_recording, state=tk.DISABLED)
        self.record_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        self.camera_status_label = ttk.Label(cam_control_frame, text="Inactive")
        self.camera_status_label.pack(side=tk.RIGHT)
        
    def create_data_section(self, parent):
        """Create real-time data display section"""
        data_frame = ttk.LabelFrame(parent, text="Real-time Data", padding=10)
        data_frame.pack(fill=tk.X, pady=5)
        
        # Initialize data variables
        self.data_vars = {
            'h_value': tk.StringVar(value="0.500"),
            'pwm_output': tk.StringVar(value="45.0%"),
            'system_state': tk.StringVar(value="STOPPED"),
            'me': tk.StringVar(value="0.300"),
            'rsi': tk.StringVar(value="0.600"),
            'pop': tk.StringVar(value="0.400"),
            'flow': tk.StringVar(value="0.500"),
            'correlation': tk.StringVar(value="0.000"),
            'efficiency': tk.StringVar(value="0.0%")
        }
        
        # Data display in organized grid
        data_items = [
            ("H Value:", self.data_vars['h_value'], 'blue'),
            ("PWM Output:", self.data_vars['pwm_output'], 'red'),
            ("System State:", self.data_vars['system_state'], 'green'),
            ("ME Feature:", self.data_vars['me'], 'black'),
            ("RSI Feature:", self.data_vars['rsi'], 'black'),
            ("POP Feature:", self.data_vars['pop'], 'black'),
            ("FLOW Feature:", self.data_vars['flow'], 'black'),
            ("H-PWM Correlation:", self.data_vars['correlation'], 'purple'),
            ("System Efficiency:", self.data_vars['efficiency'], 'orange')
        ]
        
        for i, (label, var, color) in enumerate(data_items):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(data_frame, text=label).grid(row=row, column=col, sticky='w', pady=1)
            data_label = ttk.Label(data_frame, textvariable=var, style='Data.TLabel',
                                  foreground=color)
            data_label.grid(row=row, column=col+1, sticky='e', padx=(5, 10), pady=1)
            
        data_frame.columnconfigure(1, weight=1)
        data_frame.columnconfigure(3, weight=1)
        
    def create_parameter_sections(self, parent):
        """Create categorized parameter adjustment sections"""
        param_container = ttk.LabelFrame(parent, text="Parameter Control", padding=10)
        param_container.pack(fill=tk.X, pady=5)
        
        # Create notebook for parameter categories
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
            param_notebook.add(frame, text=category.title())
            
            # Create scrollable frame for this category
            scrollable_param_frame = ScrollableFrame(frame)
            scrollable_param_frame.pack(fill=tk.BOTH, expand=True)
            
            self.create_parameter_controls(scrollable_param_frame.scrollable_frame, params)
            
    def create_parameter_controls(self, parent, params):
        """Create parameter control widgets"""
        for i, (param_name, param_info) in enumerate(params):
            # Create variable for this parameter
            if param_name not in self.param_vars:
                self.param_vars[param_name] = tk.DoubleVar(value=param_info['value'])
                
            # Parameter frame
            param_frame = ttk.Frame(parent)
            param_frame.pack(fill=tk.X, pady=2)
            
            # Label
            label_text = f"{param_name.replace('_', ' ').title()}:"
            ttk.Label(param_frame, text=label_text, width=15).pack(side=tk.LEFT)
            
            # Scale
            scale = ttk.Scale(param_frame,
                            from_=param_info['min'],
                            to=param_info['max'],
                            variable=self.param_vars[param_name],
                            orient='horizontal',
                            command=lambda val, name=param_name: self.on_parameter_change(name, val))
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            
            # Value display
            value_label = ttk.Label(param_frame, textvariable=self.param_vars[param_name], width=8)
            value_label.pack(side=tk.RIGHT)
            
            # Quick set buttons for important parameters
            if param_name in ['h_hi', 'h_lo', 'kp', 'ki']:
                quick_frame = ttk.Frame(param_frame)
                quick_frame.pack(side=tk.RIGHT, padx=(5, 0))
                
                if param_name == 'h_hi':
                    for val in [0.6, 0.65, 0.7]:
                        ttk.Button(quick_frame, text=str(val), width=4,
                                 command=lambda v=val, n=param_name: self.set_quick_value(n, v)).pack(side=tk.LEFT, padx=1)
                elif param_name == 'h_lo':
                    for val in [0.3, 0.35, 0.4]:
                        ttk.Button(quick_frame, text=str(val), width=4,
                                 command=lambda v=val, n=param_name: self.set_quick_value(n, v)).pack(side=tk.LEFT, padx=1)
                        
    def create_auto_tune_section(self, parent):
        """Create auto-tuning control section"""
        auto_frame = ttk.LabelFrame(parent, text="Auto-Tuning", padding=10)
        auto_frame.pack(fill=tk.X, pady=5)
        
        # Auto-tune toggle
        auto_control_frame = ttk.Frame(auto_frame)
        auto_control_frame.pack(fill=tk.X, pady=5)
        
        self.auto_tune_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(auto_control_frame, text="Enable Auto-Tuning",
                                    variable=self.auto_tune_var,
                                    command=self.toggle_auto_tune)
        auto_check.pack(side=tk.LEFT)
        
        self.auto_status_label = ttk.Label(auto_control_frame, text="Disabled")
        self.auto_status_label.pack(side=tk.RIGHT)
        
        # Auto-tune parameters selection
        auto_param_frame = ttk.Frame(auto_frame)
        auto_param_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(auto_param_frame, text="Auto-tune parameters:").pack(anchor='w')
        
        self.auto_param_vars = {}
        auto_params = ['kp', 'ki', 'kd', 'h_hi', 'h_lo']
        for param in auto_params:
            self.auto_param_vars[param] = tk.BooleanVar(value=param in self.auto_tune_params)
            check = ttk.Checkbutton(auto_param_frame, text=param.upper(),
                                   variable=self.auto_param_vars[param])
            check.pack(side=tk.LEFT, padx=(0, 10))
            
        # Auto-tune settings
        auto_settings_frame = ttk.Frame(auto_frame)
        auto_settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(auto_settings_frame, text="Target H-PWM Correlation:").pack(side=tk.LEFT)
        self.target_correlation_var = tk.DoubleVar(value=0.75)
        correlation_scale = ttk.Scale(auto_settings_frame, from_=0.5, to=0.95,
                                     variable=self.target_correlation_var, orient='horizontal')
        correlation_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        
        correlation_label = ttk.Label(auto_settings_frame, textvariable=self.target_correlation_var, width=6)
        correlation_label.pack(side=tk.RIGHT)
        
    def create_manual_control_section(self, parent):
        """Create manual control section"""
        manual_frame = ttk.LabelFrame(parent, text="Manual Control", padding=10)
        manual_frame.pack(fill=tk.X, pady=5)
        
        # Manual PWM control
        pwm_frame = ttk.Frame(manual_frame)
        pwm_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(pwm_frame, text="Manual PWM:").pack(side=tk.LEFT)
        self.manual_pwm_var = tk.DoubleVar(value=45.0)
        pwm_scale = ttk.Scale(pwm_frame, from_=0, to=100, variable=self.manual_pwm_var,
                             orient='horizontal', command=self.on_manual_pwm_change)
        pwm_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        
        pwm_value_label = ttk.Label(pwm_frame, textvariable=self.manual_pwm_var, width=6)
        pwm_value_label.pack(side=tk.RIGHT)
        
        # Control buttons
        control_buttons_frame = ttk.Frame(manual_frame)
        control_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_buttons_frame, text="Manual Feed",
                  command=self.manual_feed).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_buttons_frame, text="Reset All",
                  command=self.reset_all_parameters).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_buttons_frame, text="Save Config",
                  command=self.save_configuration).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_buttons_frame, text="Load Config",
                  command=self.load_configuration).pack(side=tk.RIGHT)
        
    def create_chart_section(self, parent):
        """Create enhanced chart display section"""
        chart_frame = ttk.LabelFrame(parent, text="Data Visualization", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for multiple chart views
        self.chart_notebook = ttk.Notebook(chart_frame)
        self.chart_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main monitoring tab
        main_tab = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(main_tab, text="Main Monitor")
        self.create_main_charts(main_tab)
        
        # Feature analysis tab
        feature_tab = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(feature_tab, text="Feature Analysis")
        self.create_feature_charts(feature_tab)
        
        # Performance analysis tab
        performance_tab = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(performance_tab, text="Performance")
        self.create_performance_charts(performance_tab)
        
        # Parameter evolution tab
        param_tab = ttk.Frame(self.chart_notebook)
        self.chart_notebook.add(param_tab, text="Parameters")
        self.create_parameter_charts(param_tab)
        
    def create_main_charts(self, parent):
        """Create main monitoring charts"""
        self.main_fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.main_fig.suptitle('System Performance Monitoring')
        
        # H-value chart
        self.ax1.set_title('H Value and Thresholds')
        self.ax1.set_ylabel('H Value')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend()
        
        # PWM chart
        self.ax2.set_title('PWM Output')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('PWM (%)')
        self.ax2.grid(True, alpha=0.3)
        
        self.main_canvas = FigureCanvasTkAgg(self.main_fig, parent)
        self.main_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_feature_charts(self, parent):
        """Create feature analysis charts"""
        self.feature_fig, self.feature_axes = plt.subplots(2, 2, figsize=(12, 8))
        self.feature_fig.suptitle('Feature Analysis')
        
        feature_names = ['ME', 'RSI', 'POP', 'FLOW']
        for ax, name in zip(self.feature_axes.flat, feature_names):
            ax.set_title(f'{name} Feature')
            ax.set_ylabel(name)
            ax.grid(True, alpha=0.3)
            
        self.feature_canvas = FigureCanvasTkAgg(self.feature_fig, parent)
        self.feature_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_performance_charts(self, parent):
        """Create performance analysis charts"""
        self.performance_fig, ((self.perf_ax1, self.perf_ax2), 
                              (self.perf_ax3, self.perf_ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        self.performance_fig.suptitle('Performance Analysis')
        
        self.perf_ax1.set_title('H-PWM Correlation')
        self.perf_ax2.set_title('System Efficiency')
        self.perf_ax3.set_title('Response Time')
        self.perf_ax4.set_title('Parameter Stability')
        
        for ax in [self.perf_ax1, self.perf_ax2, self.perf_ax3, self.perf_ax4]:
            ax.grid(True, alpha=0.3)
            
        self.performance_canvas = FigureCanvasTkAgg(self.performance_fig, parent)
        self.performance_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_parameter_charts(self, parent):
        """Create parameter evolution charts"""
        self.param_fig, self.param_axes = plt.subplots(2, 2, figsize=(12, 8))
        self.param_fig.suptitle('Parameter Evolution')
        
        param_groups = [['h_hi', 'h_lo'], ['kp', 'ki'], ['alpha', 'beta'], ['gamma', 'delta']]
        titles = ['Thresholds', 'PID Gains', 'Primary Weights', 'Secondary Weights']
        
        for ax, group, title in zip(self.param_axes.flat, param_groups, titles):
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            
        self.param_canvas = FigureCanvasTkAgg(self.param_fig, parent)
        self.param_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Label(self.root, text="Advanced Aqua Feeder System Ready",
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def initialize_variables(self):
        """Initialize all GUI variables"""
        # Initialize parameter variables
        for param_name, param_info in self.parameters.items():
            if param_name not in self.param_vars:
                self.param_vars[param_name] = tk.DoubleVar(value=param_info['value'])
                
    # Event handlers and control methods continue in next part...
    
    def start_system(self):
        """Start the feeding system"""
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_vars['system'].set("Running")
        self.status_vars['pwm'].set("Initialized")
        
        # Apply current parameters to simulator
        self.apply_parameters_to_simulator()
        
        print(f"System started in {self.mode} mode")
        self.update_status_bar("System started successfully")
        
    def stop_system(self):
        """Stop the feeding system"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_vars['system'].set("Stopped")
        self.status_vars['pwm'].set("Not Initialized")
        
        print("System stopped")
        self.update_status_bar("System stopped")
        
    def emergency_stop(self):
        """Emergency stop function"""
        self.stop_system()
        self.manual_pwm_var.set(0)
        self.on_manual_pwm_change(0)
        self.status_vars['safety'].set("Emergency Stop")
        
        print("EMERGENCY STOP ACTIVATED")
        self.update_status_bar("EMERGENCY STOP - System halted")
        
    def on_mode_change(self, event=None):
        """Handle mode change"""
        self.mode = self.mode_var.get()
        print(f"Mode changed to: {self.mode}")
        
        if self.use_camera:
            self.stop_camera()
            
        # Update interface based on mode
        if self.mode == "hardware":
            self.status_vars['camera'].set("Hardware Ready")
        else:
            self.status_vars['camera'].set("Simulation Ready")
            
        self.update_status_bar(f"Mode changed to {self.mode}")
        
    def on_parameter_change(self, param_name, value):
        """Handle parameter change"""
        try:
            float_value = float(value)
            self.parameters[param_name]['value'] = float_value
            
            # Apply to simulator if running
            if self.is_running:
                self.apply_parameters_to_simulator()
                
            print(f"Parameter {param_name} changed to {float_value:.3f}")
            
        except ValueError:
            pass
            
    def set_quick_value(self, param_name, value):
        """Set parameter to quick value"""
        self.param_vars[param_name].set(value)
        self.on_parameter_change(param_name, value)
        
    def apply_parameters_to_simulator(self):
        """Apply current parameters to simulator"""
        if hasattr(self.simulator, 'set_parameters'):
            params = {name: info['value'] for name, info in self.parameters.items()}
            self.simulator.set_parameters(**params)
            
    def toggle_auto_tune(self):
        """Toggle auto-tuning feature"""
        self.auto_tune_enabled = self.auto_tune_var.get()
        
        if self.auto_tune_enabled:
            self.auto_status_label.config(text="Active")
            print("Auto-tuning enabled")
            self.start_auto_tune()
        else:
            self.auto_status_label.config(text="Disabled")
            print("Auto-tuning disabled")
            
    def start_auto_tune(self):
        """Start auto-tuning process"""
        def auto_tune_loop():
            while self.auto_tune_enabled and self.is_running:
                # Implement auto-tuning algorithm here
                # This is a simplified example
                
                # Calculate current correlation
                if len(self.h_data) > 10 and len(self.pwm_data) > 10:
                    correlation = np.corrcoef(self.h_data[-50:], self.pwm_data[-50:])[0, 1]
                    target = self.target_correlation_var.get()
                    
                    if abs(correlation) < target:
                        # Adjust parameters slightly
                        if self.auto_param_vars['kp'].get():
                            current_kp = self.param_vars['kp'].get()
                            new_kp = current_kp * (1 + 0.01 * (target - abs(correlation)))
                            new_kp = max(1.0, min(50.0, new_kp))
                            self.param_vars['kp'].set(new_kp)
                            
                time.sleep(5)  # Auto-tune every 5 seconds
                
        if self.auto_tune_enabled:
            threading.Thread(target=auto_tune_loop, daemon=True).start()
            
    def toggle_camera(self):
        """Toggle camera on/off"""
        if not self.use_camera:
            self.start_camera()
        else:
            self.stop_camera()
            
    def start_camera(self):
        """Start camera capture"""
        try:
            if self.mode == "hardware":
                device = self.camera_device_var.get()
                self.camera = cv2.VideoCapture(device)
                if self.camera.isOpened():
                    self.use_camera = True
                    self.camera_btn.config(text="Stop Camera")
                    self.record_btn.config(state=tk.NORMAL)
                    self.camera_status_label.config(text="Hardware Active")
                    self.status_vars['camera'].set("Connected")
                    print(f"Hardware camera {device} started")
                else:
                    raise Exception(f"Cannot open camera device {device}")
            else:
                self.use_camera = True
                self.camera_btn.config(text="Stop Camera")
                self.record_btn.config(state=tk.NORMAL)
                self.camera_status_label.config(text="Simulation Active")
                self.status_vars['camera'].set("Simulation")
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
        self.record_btn.config(state=tk.DISABLED)
        self.camera_status_label.config(text="Inactive")
        self.status_vars['camera'].set("Disconnected")
        self.camera_label.config(image='', text="Camera Not Active")
        print("Camera stopped")
        
    def toggle_recording(self):
        """Toggle video recording"""
        # Implement video recording functionality
        print("Recording toggle - feature to be implemented")
        
    def start_camera_update(self):
        """Start camera update thread"""
        def update_camera():
            while True:
                if self.use_camera:
                    try:
                        if self.mode == "hardware" and self.camera:
                            ret, frame = self.camera.read()
                            if ret:
                                self.display_camera_frame(frame)
                        else:
                            # Get simulation frame from enhanced simulator
                            frame = self.simulator.get_camera_frame()
                            if frame is not None:
                                self.display_camera_frame(frame)
                    except Exception as e:
                        print(f"Camera update error: {e}")
                time.sleep(0.033)  # ~30 FPS
                
        thread = threading.Thread(target=update_camera, daemon=True)
        thread.start()
        
    def display_camera_frame(self, frame):
        """Display camera frame in GUI"""
        try:
            # Resize frame for display (smaller for scrollable interface)
            frame_resized = cv2.resize(frame, (280, 210))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL and then PhotoImage
            pil_image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image=pil_image)
            
            # Update display (must be in main thread)
            self.root.after(0, lambda: self.camera_label.config(image=photo, text=''))
            self.root.after(0, lambda: setattr(self.camera_label, 'image', photo))
            
        except Exception as e:
            print(f"Display frame error: {e}")
            
    def on_manual_pwm_change(self, value):
        """Handle manual PWM change"""
        if self.mode == "hardware":
            # Send PWM signal to hardware
            pwm_value = float(value)
            print(f"Manual PWM output: {pwm_value:.1f}%")
            # TODO: Implement actual hardware PWM control
            
    def manual_feed(self):
        """Trigger manual feeding"""
        if hasattr(self.simulator, 'manual_feed'):
            self.simulator.manual_feed()
        print("Manual feeding triggered")
        self.update_status_bar("Manual feeding executed")
        
    def reset_all_parameters(self):
        """Reset all parameters to default values"""
        for param_name, param_info in self.parameters.items():
            self.param_vars[param_name].set(param_info['value'])
            
        self.apply_parameters_to_simulator()
        print("All parameters reset to defaults")
        self.update_status_bar("Parameters reset to defaults")
        
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                config = {
                    'parameters': {name: var.get() for name, var in self.param_vars.items()},
                    'mode': self.mode,
                    'auto_tune_enabled': self.auto_tune_enabled,
                    'auto_tune_params': [name for name, var in self.auto_param_vars.items() if var.get()]
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                print(f"Configuration saved to {filename}")
                self.update_status_bar("Configuration saved successfully")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {str(e)}")
            
    def load_configuration(self):
        """Load configuration from file"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)
                    
                # Load parameters
                for name, value in config.get('parameters', {}).items():
                    if name in self.param_vars:
                        self.param_vars[name].set(value)
                        
                # Load mode
                if 'mode' in config:
                    self.mode_var.set(config['mode'])
                    self.on_mode_change()
                    
                # Load auto-tune settings
                if 'auto_tune_enabled' in config:
                    self.auto_tune_var.set(config['auto_tune_enabled'])
                    
                self.apply_parameters_to_simulator()
                print(f"Configuration loaded from {filename}")
                self.update_status_bar("Configuration loaded successfully")
                
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load configuration: {str(e)}")
            
    def start_data_update(self):
        """Start data update loop"""
        def update_data():
            if self.is_running:
                # Get current state from simulator
                state = self.simulator.get_current_state()
                
                # Update data displays
                self.data_vars['h_value'].set(f"{state['h_value']:.3f}")
                self.data_vars['pwm_output'].set(f"{state['pwm_output']:.1f}%")
                self.data_vars['system_state'].set(state.get('state', 'UNKNOWN'))
                
                features = state.get('features', {})
                self.data_vars['me'].set(f"{features.get('ME', 0):.3f}")
                self.data_vars['rsi'].set(f"{features.get('RSI', 0):.3f}")
                self.data_vars['pop'].set(f"{features.get('POP', 0):.3f}")
                self.data_vars['flow'].set(f"{features.get('FLOW', 0):.3f}")
                
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
                
                # Calculate correlation and efficiency
                if len(self.h_data) > 10:
                    correlation = np.corrcoef(self.h_data[-50:], self.pwm_data[-50:])[0, 1]
                    self.data_vars['correlation'].set(f"{correlation:.3f}")
                    
                    # Simple efficiency calculation
                    h_variance = np.var(self.h_data[-20:])
                    efficiency = max(0, 100 * (1 - h_variance * 10))
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
                self.update_all_charts()
                
            # Schedule next update
            self.root.after(100, update_data)
            
        # Start the update loop
        self.root.after(100, update_data)
        
    def update_all_charts(self):
        """Update all chart displays"""
        try:
            if len(self.time_data) > 1:
                self.update_main_charts()
                self.update_feature_charts()
                self.update_performance_charts()
                self.update_parameter_charts()
                
        except Exception as e:
            print(f"Chart update error: {e}")
            
    def update_main_charts(self):
        """Update main monitoring charts"""
        # Clear and update H-value chart
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
        
        # Clear and update PWM chart
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
        
    def update_feature_charts(self):
        """Update feature analysis charts"""
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
        
    def update_performance_charts(self):
        """Update performance analysis charts"""
        if len(self.h_data) > 10:
            # H-PWM correlation over time
            correlations = []
            window_size = 20
            for i in range(window_size, len(self.h_data)):
                corr = np.corrcoef(self.h_data[i-window_size:i], 
                                 self.pwm_data[i-window_size:i])[0, 1]
                correlations.append(corr)
                
            if correlations:
                self.perf_ax1.clear()
                self.perf_ax1.plot(self.time_data[window_size:], correlations, 'purple', linewidth=2)
                self.perf_ax1.axhline(y=self.target_correlation_var.get(), color='red', 
                                     linestyle='--', alpha=0.7, label='Target')
                self.perf_ax1.set_title('H-PWM Correlation')
                self.perf_ax1.set_ylabel('Correlation')
                self.perf_ax1.grid(True, alpha=0.3)
                self.perf_ax1.legend()
                
        self.performance_canvas.draw()
        
    def update_parameter_charts(self):
        """Update parameter evolution charts"""
        # This would show parameter changes over time
        # Implementation depends on tracking parameter history
        pass
        
    def update_status_bar(self, message):
        """Update status bar with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.config(text=f"[{timestamp}] {message}")
        
    def run(self):
        """Start the GUI application"""
        print("Starting Advanced Aqua Feeder Control System...")
        print("Features: Scrollable interface, enhanced parameter management")
        self.root.mainloop()
        
    def __del__(self):
        """Cleanup on exit"""
        if self.camera:
            self.camera.release()


def main():
    """Main entry point"""
    try:
        app = AdvancedAquaFeederGUI()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Application Error", f"Failed to start application: {str(e)}")


if __name__ == "__main__":
    main()
