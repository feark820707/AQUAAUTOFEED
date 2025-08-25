#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent Aquaculture Auto-Feeding Control System - Enhanced GUI
Features ASCII output and camera display to avoid encoding issues
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
try:
    from gui.simulator import SystemSimulator
    from gui.config_editor import ConfigEditor
    from gui.log_viewer import LogViewer
except ImportError:
    # Mock fallbacks if modules not available
    class SystemSimulator:
        def __init__(self):
            self.h_value = 0.5
            self.pwm_output = 45
            self.features = {'ME': 0.3, 'RSI': 0.6, 'POP': 0.4, 'FLOW': 0.5}
            
        def get_current_state(self):
            return {
                'h_value': self.h_value,
                'pwm_output': self.pwm_output,
                'features': self.features,
                'state': 'EVALUATION'
            }
    
    ConfigEditor = None
    LogViewer = None


class EnhancedAquaFeederGUI:
    """Enhanced GUI with Camera Display and ASCII Output"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_main_window()
        
        # System status
        self.is_running = False
        self.mode = "simulation"  # "simulation" or "hardware"
        self.simulator = SystemSimulator()
        
        # Camera related
        self.camera = None
        self.camera_frame = None
        self.camera_label = None
        self.use_camera = False
        
        # Data storage
        self.time_data = []
        self.h_data = []
        self.pwm_data = []
        self.feature_data = {'ME': [], 'RSI': [], 'POP': [], 'FLOW': []}
        
        # GUI Variables
        self.status_vars = {}
        self.data_vars = {}
        self.param_vars = {}
        
        # Create interface components
        self.create_main_interface()
        self.create_status_bar()
        
        # Start update loops
        self.start_camera_update()
        self.start_data_update()
        
        print("Aqua Feeder Control System - GUI Initialized")
        
    def setup_main_window(self):
        """Setup main window properties with ASCII safe configuration"""
        self.root.title("Aqua Feeder Control System v1.0")
        self.root.geometry("1600x1000")
        self.root.minsize(1400, 900)
        
        # Configure styles using ASCII safe fonts
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Status.TLabel', font=('Consolas', 9))
        style.configure('Data.TLabel', font=('Consolas', 12, 'bold'))
        
    def create_main_interface(self):
        """Create main interface layout"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for controls and camera
        left_panel = ttk.Frame(main_frame, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right panel for charts
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create components
        self.create_control_section(left_panel)
        self.create_camera_section(left_panel)
        self.create_data_section(left_panel)
        self.create_parameter_section(left_panel)
        self.create_chart_section(right_panel)
        
    def create_control_section(self, parent):
        """Create system control section"""
        control_frame = ttk.LabelFrame(parent, text="System Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        
        self.start_btn = ttk.Button(button_frame, text="Start System", 
                                   command=self.start_system, style='Header.TLabel')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop System", 
                                  command=self.stop_system, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status indicators
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_vars['system'] = tk.StringVar(value="Stopped")
        self.status_vars['camera'] = tk.StringVar(value="Disconnected")
        self.status_vars['pwm'] = tk.StringVar(value="Not Initialized")
        
        ttk.Label(status_frame, text="System:").grid(row=0, column=0, sticky='w')
        ttk.Label(status_frame, textvariable=self.status_vars['system'], 
                 style='Status.TLabel').grid(row=0, column=1, sticky='w', padx=(10, 0))
        
        ttk.Label(status_frame, text="Camera:").grid(row=1, column=0, sticky='w')
        ttk.Label(status_frame, textvariable=self.status_vars['camera'], 
                 style='Status.TLabel').grid(row=1, column=1, sticky='w', padx=(10, 0))
        
        ttk.Label(status_frame, text="PWM:").grid(row=2, column=0, sticky='w')
        ttk.Label(status_frame, textvariable=self.status_vars['pwm'], 
                 style='Status.TLabel').grid(row=2, column=1, sticky='w', padx=(10, 0))
        
    def create_camera_section(self, parent):
        """Create camera display section"""
        camera_frame = ttk.LabelFrame(parent, text="Camera View", padding=10)
        camera_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Camera display area
        self.camera_label = ttk.Label(camera_frame, text="Camera Not Active")
        self.camera_label.pack(pady=20)
        
        # Camera controls
        cam_control_frame = ttk.Frame(camera_frame)
        cam_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.camera_btn = ttk.Button(cam_control_frame, text="Start Camera", 
                                    command=self.toggle_camera)
        self.camera_btn.pack(side=tk.LEFT)
        
        self.camera_status = ttk.Label(cam_control_frame, text="Inactive")
        self.camera_status.pack(side=tk.RIGHT)
        
    def create_data_section(self, parent):
        """Create real-time data display section"""
        data_frame = ttk.LabelFrame(parent, text="Real-time Data", padding=10)
        data_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Initialize data variables
        self.data_vars['h_value'] = tk.StringVar(value="0.500")
        self.data_vars['pwm_output'] = tk.StringVar(value="45.0%")
        self.data_vars['me'] = tk.StringVar(value="0.300")
        self.data_vars['rsi'] = tk.StringVar(value="0.600")
        self.data_vars['pop'] = tk.StringVar(value="0.400")
        self.data_vars['flow'] = tk.StringVar(value="0.500")
        
        # Data display grid
        row = 0
        for label, var in [("H Value:", self.data_vars['h_value']),
                          ("PWM Output:", self.data_vars['pwm_output']),
                          ("ME Feature:", self.data_vars['me']),
                          ("RSI Feature:", self.data_vars['rsi']),
                          ("POP Feature:", self.data_vars['pop']),
                          ("FLOW Feature:", self.data_vars['flow'])]:
            ttk.Label(data_frame, text=label).grid(row=row, column=0, sticky='w', pady=2)
            ttk.Label(data_frame, textvariable=var, style='Data.TLabel').grid(
                row=row, column=1, sticky='e', padx=(10, 0), pady=2)
            row += 1
            
        data_frame.columnconfigure(1, weight=1)
        
    def create_parameter_section(self, parent):
        """Create parameter adjustment section"""
        param_frame = ttk.LabelFrame(parent, text="Parameter Adjustment", padding=10)
        param_frame.pack(fill=tk.BOTH, expand=True)
        
        # Parameter controls
        self.param_vars['h_hi'] = tk.DoubleVar(value=0.65)
        self.param_vars['h_lo'] = tk.DoubleVar(value=0.35)
        self.param_vars['kp'] = tk.DoubleVar(value=15.0)
        self.param_vars['ki'] = tk.DoubleVar(value=2.0)
        
        params = [
            ("H High Threshold:", self.param_vars['h_hi'], 0.5, 0.8, 0.01),
            ("H Low Threshold:", self.param_vars['h_lo'], 0.2, 0.5, 0.01),
            ("Kp (Proportional):", self.param_vars['kp'], 1.0, 30.0, 0.5),
            ("Ki (Integral):", self.param_vars['ki'], 0.1, 10.0, 0.1)
        ]
        
        for i, (label, var, min_val, max_val, resolution) in enumerate(params):
            ttk.Label(param_frame, text=label).grid(row=i*2, column=0, sticky='w', pady=(5, 0))
            
            scale_frame = ttk.Frame(param_frame)
            scale_frame.grid(row=i*2+1, column=0, sticky='ew', pady=(0, 5))
            
            scale = ttk.Scale(scale_frame, from_=min_val, to=max_val, 
                            variable=var, orient='horizontal')
            scale.pack(fill=tk.X, side=tk.LEFT, expand=True)
            
            value_label = ttk.Label(scale_frame, textvariable=var, width=6)
            value_label.pack(side=tk.RIGHT, padx=(5, 0))
            
        param_frame.columnconfigure(0, weight=1)
        
        # Manual controls
        manual_frame = ttk.Frame(param_frame)
        manual_frame.grid(row=len(params)*2, column=0, sticky='ew', pady=(10, 0))
        
        ttk.Button(manual_frame, text="Manual Feed", 
                  command=self.manual_feed).pack(side=tk.LEFT)
        ttk.Button(manual_frame, text="Reset Parameters", 
                  command=self.reset_parameters).pack(side=tk.RIGHT)
        
    def create_chart_section(self, parent):
        """Create chart display section"""
        chart_frame = ttk.LabelFrame(parent, text="Data Visualization", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for multiple charts
        notebook = ttk.Notebook(chart_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main chart tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main Charts")
        self.create_main_charts(main_tab)
        
        # Feature chart tab
        feature_tab = ttk.Frame(notebook)
        notebook.add(feature_tab, text="Feature Analysis")
        self.create_feature_charts(feature_tab)
        
    def create_main_charts(self, parent):
        """Create main H-value and PWM charts"""
        self.main_fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.main_fig.suptitle('System Performance Monitoring')
        
        # H-value chart
        self.ax1.set_title('H Value Over Time')
        self.ax1.set_ylabel('H Value')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.axhline(y=0.65, color='r', linestyle='--', alpha=0.7, label='H_hi')
        self.ax1.axhline(y=0.35, color='b', linestyle='--', alpha=0.7, label='H_lo')
        self.ax1.legend()
        
        # PWM chart
        self.ax2.set_title('PWM Output Over Time')
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
        for i, (ax, name) in enumerate(zip(self.feature_axes.flat, feature_names)):
            ax.set_title(f'{name} Feature')
            ax.set_ylabel(name)
            ax.grid(True, alpha=0.3)
            if i >= 2:
                ax.set_xlabel('Time (s)')
        
        self.feature_canvas = FigureCanvasTkAgg(self.feature_fig, parent)
        self.feature_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Label(self.root, text="System Ready", 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
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
                self.camera = cv2.VideoCapture(0)
                if self.camera.isOpened():
                    self.use_camera = True
                    self.camera_btn.config(text="Stop Camera")
                    self.camera_status.config(text="Active")
                    self.status_vars['camera'].set("Connected")
                    print("Camera started successfully")
                else:
                    raise Exception("Cannot open camera")
            else:
                # Simulation mode - generate test pattern
                self.use_camera = True
                self.camera_btn.config(text="Stop Camera")
                self.camera_status.config(text="Simulation")
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
        self.camera_status.config(text="Inactive")
        self.status_vars['camera'].set("Disconnected")
        self.camera_label.config(image='', text="Camera Not Active")
        print("Camera stopped")
        
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
                            # Generate simulation frame
                            frame = self.generate_simulation_frame()
                            self.display_camera_frame(frame)
                    except Exception as e:
                        print(f"Camera update error: {e}")
                time.sleep(0.033)  # ~30 FPS
                
        thread = threading.Thread(target=update_camera, daemon=True)
        thread.start()
        
    def generate_simulation_frame(self):
        """Generate simulated camera frame"""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:] = (20, 50, 100)  # Dark blue background
        
        # Add some moving elements to simulate fish
        t = time.time()
        for i in range(3):
            x = int(160 + 80 * np.sin(t + i * 2))
            y = int(120 + 60 * np.cos(t * 0.7 + i))
            cv2.circle(frame, (x, y), 15, (100, 150, 200), -1)
            
        # Add current H value as overlay
        h_val = self.simulator.get_current_state()['h_value']
        cv2.putText(frame, f"H: {h_val:.3f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
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
            
    def start_system(self):
        """Start the feeding system"""
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_vars['system'].set("Running")
        self.status_vars['pwm'].set("Initialized")
        
        if self.mode == "simulation":
            print("System started in simulation mode")
        else:
            print("System started in hardware mode")
            
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
        
    def on_mode_change(self, event=None):
        """Handle mode change"""
        self.mode = self.mode_var.get()
        print(f"Mode changed to: {self.mode}")
        
        if self.use_camera:
            self.stop_camera()
            
        self.update_status_bar(f"Mode changed to {self.mode}")
        
    def manual_feed(self):
        """Trigger manual feeding"""
        print("Manual feeding triggered")
        self.update_status_bar("Manual feeding executed")
        
    def reset_parameters(self):
        """Reset all parameters to default values"""
        self.param_vars['h_hi'].set(0.65)
        self.param_vars['h_lo'].set(0.35)
        self.param_vars['kp'].set(15.0)
        self.param_vars['ki'].set(2.0)
        print("Parameters reset to defaults")
        self.update_status_bar("Parameters reset to defaults")
        
    def start_data_update(self):
        """Start data update loop"""
        def update_data():
            if self.is_running:
                # Get current state from simulator
                state = self.simulator.get_current_state()
                
                # Update data displays
                self.data_vars['h_value'].set(f"{state['h_value']:.3f}")
                self.data_vars['pwm_output'].set(f"{state['pwm_output']:.1f}%")
                self.data_vars['me'].set(f"{state['features']['ME']:.3f}")
                self.data_vars['rsi'].set(f"{state['features']['RSI']:.3f}")
                self.data_vars['pop'].set(f"{state['features']['POP']:.3f}")
                self.data_vars['flow'].set(f"{state['features']['FLOW']:.3f}")
                
                # Update data arrays for plotting
                current_time = time.time()
                if not hasattr(self, 'start_time'):
                    self.start_time = current_time
                    
                elapsed_time = current_time - self.start_time
                
                self.time_data.append(elapsed_time)
                self.h_data.append(state['h_value'])
                self.pwm_data.append(state['pwm_output'])
                
                for feature, value in state['features'].items():
                    self.feature_data[feature].append(value)
                
                # Keep only last 100 points
                if len(self.time_data) > 100:
                    self.time_data = self.time_data[-100:]
                    self.h_data = self.h_data[-100:]
                    self.pwm_data = self.pwm_data[-100:]
                    for feature in self.feature_data:
                        self.feature_data[feature] = self.feature_data[feature][-100:]
                
                # Update charts
                self.update_charts()
                
            # Schedule next update
            self.root.after(100, update_data)
            
        # Start the update loop
        self.root.after(100, update_data)
        
    def update_charts(self):
        """Update chart displays"""
        try:
            if len(self.time_data) > 1:
                # Update main charts
                self.ax1.clear()
                self.ax1.plot(self.time_data, self.h_data, 'b-', linewidth=2, label='H Value')
                self.ax1.axhline(y=self.param_vars['h_hi'].get(), color='r', 
                               linestyle='--', alpha=0.7, label='H_hi')
                self.ax1.axhline(y=self.param_vars['h_lo'].get(), color='g', 
                               linestyle='--', alpha=0.7, label='H_lo')
                self.ax1.set_title('H Value Over Time')
                self.ax1.set_ylabel('H Value')
                self.ax1.grid(True, alpha=0.3)
                self.ax1.legend()
                
                self.ax2.clear()
                self.ax2.plot(self.time_data, self.pwm_data, 'r-', linewidth=2, label='PWM Output')
                self.ax2.set_title('PWM Output Over Time')
                self.ax2.set_xlabel('Time (s)')
                self.ax2.set_ylabel('PWM (%)')
                self.ax2.grid(True, alpha=0.3)
                self.ax2.legend()
                
                # Update feature charts
                colors = ['blue', 'green', 'orange', 'purple']
                feature_names = ['ME', 'RSI', 'POP', 'FLOW']
                
                for i, (ax, name, color) in enumerate(zip(self.feature_axes.flat, 
                                                         feature_names, colors)):
                    ax.clear()
                    if name in self.feature_data and len(self.feature_data[name]) > 0:
                        ax.plot(self.time_data, self.feature_data[name], 
                               color=color, linewidth=2, label=name)
                    ax.set_title(f'{name} Feature')
                    ax.set_ylabel(name)
                    ax.grid(True, alpha=0.3)
                    if i >= 2:
                        ax.set_xlabel('Time (s)')
                    ax.legend()
                
                # Redraw canvases
                self.main_canvas.draw()
                self.feature_canvas.draw()
                
        except Exception as e:
            print(f"Chart update error: {e}")
            
    def update_status_bar(self, message):
        """Update status bar message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.config(text=f"[{timestamp}] {message}")
        
    def run(self):
        """Start the GUI application"""
        print("Starting Aqua Feeder Control System GUI...")
        print("System ready for operation")
        self.root.mainloop()
        
    def __del__(self):
        """Cleanup on exit"""
        if self.camera:
            self.camera.release()


def main():
    """Main entry point"""
    print("=" * 50)
    print("Aqua Feeder Control System v1.0")
    print("Enhanced GUI with Camera Display")
    print("=" * 50)
    
    try:
        app = EnhancedAquaFeederGUI()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Application Error", f"Failed to start application: {str(e)}")


if __name__ == "__main__":
    main()
