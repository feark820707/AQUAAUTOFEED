#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camera Test Program for Aqua Feeder System
Test both hardware and simulation camera modes
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import threading
import time
from PIL import Image, ImageTk

class CameraTestGUI:
    """Simple camera test interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Camera Test - Aqua Feeder System")
        self.root.geometry("800x600")
        
        # Camera variables
        self.camera = None
        self.use_camera = False
        self.camera_mode = "simulation"
        
        self.create_interface()
        self.start_camera_thread()
        
    def create_interface(self):
        """Create the test interface"""
        # Title
        title_label = tk.Label(self.root, text="Camera Test Program", 
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # Mode selection
        tk.Label(control_frame, text="Camera Mode:").pack(side=tk.LEFT, padx=(0, 10))
        self.mode_var = tk.StringVar(value="simulation")
        mode_combo = ttk.Combobox(control_frame, textvariable=self.mode_var,
                                 values=["simulation", "hardware"], state="readonly")
        mode_combo.pack(side=tk.LEFT, padx=(0, 20))
        mode_combo.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Camera control buttons
        self.start_btn = tk.Button(control_frame, text="Start Camera", 
                                  command=self.start_camera, bg='lightgreen')
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(control_frame, text="Stop Camera", 
                                 command=self.stop_camera, bg='lightcoral')
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # Status
        self.status_label = tk.Label(control_frame, text="Camera: Inactive", 
                                    font=('Arial', 10, 'bold'))
        self.status_label.pack(side=tk.RIGHT, padx=20)
        
        # Camera display area
        camera_frame = tk.LabelFrame(self.root, text="Camera View", padx=10, pady=10)
        camera_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.camera_label = tk.Label(camera_frame, text="Camera Not Active", 
                                    bg='black', fg='white', width=80, height=20)
        self.camera_label.pack(padx=10, pady=10)
        
        # Info area
        info_frame = tk.LabelFrame(self.root, text="Camera Information", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        self.info_text.pack(fill=tk.X)
        
        self.update_info("Camera test program ready\n- Select camera mode (simulation/hardware)\n- Click 'Start Camera' to begin\n- Simulation mode shows animated fish")
        
    def on_mode_change(self, event=None):
        """Handle mode change"""
        self.camera_mode = self.mode_var.get()
        if self.use_camera:
            self.stop_camera()
        self.update_info(f"Camera mode changed to: {self.camera_mode}")
        
    def start_camera(self):
        """Start camera capture"""
        try:
            if self.camera_mode == "hardware":
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened():
                    raise Exception("Cannot open hardware camera (device 0)")
                    
                # Set camera properties
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                self.use_camera = True
                self.status_label.config(text="Camera: Hardware Active", fg='green')
                self.update_info("Hardware camera started successfully")
                
            else:  # simulation mode
                self.use_camera = True
                self.status_label.config(text="Camera: Simulation Active", fg='blue')
                self.update_info("Simulation camera started - showing animated aquarium scene")
                
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
                
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            self.update_info(f"Camera error: {str(e)}")
            
    def stop_camera(self):
        """Stop camera capture"""
        self.use_camera = False
        if self.camera:
            self.camera.release()
            self.camera = None
            
        self.status_label.config(text="Camera: Inactive", fg='black')
        self.camera_label.config(image='', text="Camera Not Active")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_info("Camera stopped")
        
    def start_camera_thread(self):
        """Start camera update thread"""
        def camera_loop():
            while True:
                if self.use_camera:
                    try:
                        if self.camera_mode == "hardware" and self.camera:
                            ret, frame = self.camera.read()
                            if ret:
                                self.display_frame(frame)
                            else:
                                self.update_info("Failed to read from hardware camera")
                        else:
                            # Generate simulation frame
                            frame = self.generate_simulation_frame()
                            self.display_frame(frame)
                    except Exception as e:
                        self.update_info(f"Camera update error: {e}")
                        
                time.sleep(0.033)  # ~30 FPS
                
        thread = threading.Thread(target=camera_loop, daemon=True)
        thread.start()
        
    def generate_simulation_frame(self):
        """Generate realistic aquarium simulation"""
        # Create blue aquarium background
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (45, 85, 125)  # Deep blue water
        
        # Add water surface effect
        for y in range(50):
            wave = int(5 * np.sin(time.time() * 2 + y * 0.1))
            frame[y, :] = (60 + wave, 120 + wave, 180 + wave)
            
        # Add fish with realistic movement
        t = time.time()
        fish_count = 8
        
        for i in range(fish_count):
            # Each fish has different movement pattern
            speed_x = 0.3 + 0.2 * np.sin(i)
            speed_y = 0.2 + 0.1 * np.cos(i)
            
            x = int(320 + 200 * np.sin(t * speed_x + i * 0.8))
            y = int(240 + 150 * np.cos(t * speed_y + i * 1.2))
            
            # Keep fish in frame
            x = max(50, min(590, x))
            y = max(80, min(400, y))
            
            # Fish body (ellipse)
            fish_color = (150 + i * 10, 180 + i * 8, 200 + i * 5)
            cv2.ellipse(frame, (x, y), (25, 12), int(t * 20 + i * 30), 0, 360, fish_color, -1)
            
            # Fish tail
            tail_x = int(x - 20 * np.cos(t * 3 + i))
            tail_y = int(y + 5 * np.sin(t * 3 + i))
            cv2.line(frame, (x - 20, y), (tail_x, tail_y), fish_color, 3)
            
            # Fish eye
            cv2.circle(frame, (x + 8, y - 3), 3, (255, 255, 255), -1)
            cv2.circle(frame, (x + 8, y - 3), 1, (0, 0, 0), -1)
            
        # Add bubbles
        for i in range(15):
            bubble_x = int(100 + i * 40 + 10 * np.sin(t * 2 + i))
            bubble_y = int(450 - ((t * 50 + i * 30) % 400))
            bubble_size = int(2 + 3 * np.sin(t + i))
            cv2.circle(frame, (bubble_x, bubble_y), bubble_size, (200, 200, 200), 1)
            
        # Add aquarium plants
        for i in range(4):
            plant_x = 50 + i * 150
            for j in range(10):
                plant_y = 450 - j * 15
                sway = int(10 * np.sin(t + i + j * 0.3))
                cv2.line(frame, (plant_x + sway, plant_y), 
                        (plant_x + sway, plant_y + 15), (50, 150, 50), 2)
                
        # Add system info overlay
        cv2.putText(frame, f"Aquarium Simulation Camera", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"FPS: 30", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Fish Count: {fish_count}", (10, 85), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Mode: Simulation", (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                   
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (520, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        return frame
        
    def display_frame(self, frame):
        """Display camera frame"""
        try:
            # Resize to fit display
            display_frame = cv2.resize(frame, (640, 480))
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PhotoImage
            pil_image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image=pil_image)
            
            # Update display in main thread
            self.root.after(0, lambda: self.camera_label.config(image=photo, text=''))
            self.root.after(0, lambda: setattr(self.camera_label, 'image', photo))
            
        except Exception as e:
            self.update_info(f"Display error: {e}")
            
    def update_info(self, message):
        """Update info display"""
        timestamp = time.strftime("%H:%M:%S")
        self.info_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.info_text.see(tk.END)
        
    def run(self):
        """Run the application"""
        self.root.mainloop()
        
    def __del__(self):
        """Cleanup"""
        if self.camera:
            self.camera.release()


def main():
    """Main entry point"""
    print("Starting Camera Test Program...")
    try:
        app = CameraTestGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    main()
