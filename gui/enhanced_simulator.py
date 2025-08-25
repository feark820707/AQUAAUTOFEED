#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced System Simulator with Camera Simulation
ASCII safe output and visual fish simulation
"""

import numpy as np
import cv2
import time
import threading
import random
from datetime import datetime


class EnhancedSystemSimulator:
    """Enhanced system simulator with camera and fish behavior simulation"""
    
    def __init__(self):
        # System state
        self.h_value = 0.5
        self.pwm_output = 45.0
        self.system_state = "EVALUATION"  # FEEDING, EVALUATION, STABLE
        self.last_state_change = time.time()
        
        # Control parameters
        self.h_hi = 0.65
        self.h_lo = 0.35
        self.kp = 15.0
        self.ki = 2.0
        self.integral = 0.0
        
        # Feature values
        self.features = {
            'ME': 0.3,
            'RSI': 0.6, 
            'POP': 0.4,
            'FLOW': 0.5
        }
        
        # Fish simulation
        self.fish_count = 5
        self.fish_positions = []
        self.fish_velocities = []
        self.initialize_fish()
        
        # Environment simulation
        self.feeding_activity = 0.0
        self.bubble_intensity = 0.3
        self.water_turbulence = 0.1
        
        # Camera simulation
        self.frame_width = 640
        self.frame_height = 480
        self.current_frame = None
        
        # Timing
        self.last_update = time.time()
        self.simulation_running = True
        
        # Start simulation thread
        self.start_simulation()
        
        print("Enhanced system simulator initialized")
        print("Features: Fish behavior, camera simulation, ASCII output")
        
    def initialize_fish(self):
        """Initialize fish positions and velocities"""
        self.fish_positions = []
        self.fish_velocities = []
        
        for _ in range(self.fish_count):
            # Random position within frame
            pos = [
                random.uniform(50, self.frame_width - 50),
                random.uniform(50, self.frame_height - 50)
            ]
            # Random velocity
            vel = [
                random.uniform(-2, 2),
                random.uniform(-2, 2)
            ]
            self.fish_positions.append(pos)
            self.fish_velocities.append(vel)
            
    def start_simulation(self):
        """Start simulation thread"""
        def simulation_loop():
            while self.simulation_running:
                self.update_simulation()
                time.sleep(0.05)  # 20 FPS simulation
                
        thread = threading.Thread(target=simulation_loop, daemon=True)
        thread.start()
        
    def update_simulation(self):
        """Update simulation state"""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Update fish behavior
        self.update_fish_behavior(dt)
        
        # Update features based on fish behavior
        self.update_features()
        
        # Update H value using feature fusion
        self.update_h_value()
        
        # Update control system
        self.update_control_system(dt)
        
        # Update environment
        self.update_environment()
        
        # Generate camera frame
        self.generate_camera_frame()
        
    def update_fish_behavior(self, dt):
        """Update fish positions and behavior"""
        # Simulate fish response to feeding
        activity_factor = 1.0 + self.feeding_activity * 3.0
        
        for i in range(len(self.fish_positions)):
            pos = self.fish_positions[i]
            vel = self.fish_velocities[i]
            
            # Random movement
            vel[0] += random.uniform(-0.5, 0.5) * activity_factor
            vel[1] += random.uniform(-0.5, 0.5) * activity_factor
            
            # Limit velocity
            max_vel = 3.0 * activity_factor
            vel[0] = max(-max_vel, min(max_vel, vel[0]))
            vel[1] = max(-max_vel, min(max_vel, vel[1]))
            
            # Update position
            pos[0] += vel[0] * dt * 60  # Scale for frame rate
            pos[1] += vel[1] * dt * 60
            
            # Boundary conditions (bounce off walls)
            if pos[0] < 30 or pos[0] > self.frame_width - 30:
                vel[0] = -vel[0] * 0.8
                pos[0] = max(30, min(self.frame_width - 30, pos[0]))
                
            if pos[1] < 30 or pos[1] > self.frame_height - 30:
                vel[1] = -vel[1] * 0.8
                pos[1] = max(30, min(self.frame_height - 30, pos[1]))
                
            # Damping
            vel[0] *= 0.98
            vel[1] *= 0.98
            
    def update_features(self):
        """Update feature values based on fish behavior"""
        # Calculate average fish velocity (Motion Energy)
        total_velocity = 0
        for vel in self.fish_velocities:
            total_velocity += (vel[0]**2 + vel[1]**2)**0.5
        avg_velocity = total_velocity / len(self.fish_velocities) if self.fish_velocities else 0
        
        # ME: Motion Energy (normalized)
        self.features['ME'] = min(1.0, avg_velocity / 10.0)
        
        # RSI: Ripple Spectral Index (simulated)
        ripple_base = 0.4 + 0.3 * np.sin(time.time() * 0.5)
        ripple_noise = random.uniform(-0.1, 0.1)
        self.features['RSI'] = max(0, min(1, ripple_base + ripple_noise + 
                                         self.feeding_activity * 0.3))
        
        # POP: Bubble Pop Events (simulated)
        pop_base = self.bubble_intensity + random.uniform(-0.2, 0.2)
        self.features['POP'] = max(0, min(1, pop_base + self.feeding_activity * 0.2))
        
        # FLOW: Optical Flow Inconsistency
        flow_base = 0.3 + 0.2 * np.sin(time.time() * 0.3)
        flow_variation = self.features['ME'] * 0.4 + random.uniform(-0.1, 0.1)
        self.features['FLOW'] = max(0, min(1, flow_base + flow_variation))
        
    def update_h_value(self):
        """Update H value using feature fusion"""
        # Feature fusion weights
        alpha = 0.4  # RSI weight
        beta = 0.3   # POP weight  
        gamma = 0.2  # FLOW weight
        delta = 0.1  # ME weight (subtracted)
        
        # Calculate H value
        h_raw = (alpha * self.features['RSI'] + 
                beta * self.features['POP'] + 
                gamma * self.features['FLOW'] - 
                delta * self.features['ME'])
        
        # Apply smoothing
        smoothing = 0.1
        self.h_value = (1 - smoothing) * self.h_value + smoothing * h_raw
        
        # Ensure bounds
        self.h_value = max(0, min(1, self.h_value))
        
    def update_control_system(self, dt):
        """Update PI control system"""
        current_time = time.time()
        
        # State machine logic
        if self.system_state == "FEEDING":
            if current_time - self.last_state_change > 0.6:  # 0.6s feeding
                self.system_state = "EVALUATION"
                self.last_state_change = current_time
                self.feeding_activity *= 0.7  # Decay feeding activity
                
        elif self.system_state == "EVALUATION": 
            if current_time - self.last_state_change > 3.0:  # 3s evaluation
                self.system_state = "STABLE"
                self.last_state_change = current_time
                
        elif self.system_state == "STABLE":
            if current_time - self.last_state_change > 1.0:  # 1s stable
                # Check if feeding needed
                if self.h_value > self.h_hi:
                    self.system_state = "FEEDING"
                    self.last_state_change = current_time
                    self.feeding_activity = min(1.0, self.feeding_activity + 0.5)
                else:
                    self.system_state = "EVALUATION"
                    self.last_state_change = current_time
                    
        # PI control for PWM output
        if self.system_state == "FEEDING":
            # During feeding, increase PWM
            target_pwm = 60 + (self.h_value - self.h_hi) * 40
        else:
            # Normal operation
            if self.h_value > self.h_hi:
                target_pwm = 50 + (self.h_value - self.h_hi) * 100
            elif self.h_value < self.h_lo:
                target_pwm = 30 + (self.h_lo - self.h_value) * 50
            else:
                target_pwm = 45  # Baseline
                
        # PI controller
        error = target_pwm - self.pwm_output
        self.integral += error * dt
        
        # Anti-windup
        if self.integral > 10:
            self.integral = 10
        elif self.integral < -10:
            self.integral = -10
            
        # PI output
        control_output = self.kp * error + self.ki * self.integral
        
        # Update PWM with rate limiting
        max_change = 50 * dt  # Max change per second
        if abs(control_output) > max_change:
            control_output = max_change if control_output > 0 else -max_change
            
        self.pwm_output += control_output
        
        # PWM limits
        self.pwm_output = max(20, min(70, self.pwm_output))
        
    def update_environment(self):
        """Update environment parameters"""
        # Bubble intensity varies with PWM
        target_bubbles = 0.2 + (self.pwm_output - 20) / 50 * 0.5
        self.bubble_intensity += (target_bubbles - self.bubble_intensity) * 0.1
        
        # Water turbulence
        self.water_turbulence = 0.05 + self.feeding_activity * 0.2
        
    def generate_camera_frame(self):
        """Generate simulated camera frame"""
        # Create background (water color)
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        water_color = (40, 80, 120)  # Dark blue-green
        frame[:] = water_color
        
        # Add water texture/noise
        noise = np.random.randint(-20, 20, (self.frame_height, self.frame_width, 3))
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Add bubbles
        bubble_count = int(10 + self.bubble_intensity * 20)
        for _ in range(bubble_count):
            x = random.randint(0, self.frame_width - 1)
            y = random.randint(0, self.frame_height - 1)
            radius = random.randint(2, 8)
            color = (200, 220, 255)  # Light blue bubbles
            cv2.circle(frame, (x, y), radius, color, -1)
            
        # Draw fish
        for i, pos in enumerate(self.fish_positions):
            x, y = int(pos[0]), int(pos[1])
            
            # Fish size varies with activity
            base_size = 15
            size_variation = int(5 * self.feeding_activity)
            fish_size = base_size + size_variation
            
            # Fish color (orange-red)
            fish_color = (50, 100, 200)  # BGR format
            
            # Draw fish body (ellipse)
            cv2.ellipse(frame, (x, y), (fish_size, fish_size//2), 
                       0, 0, 360, fish_color, -1)
            
            # Draw fish tail
            vel = self.fish_velocities[i]
            if vel[0] != 0 or vel[1] != 0:
                # Tail direction opposite to movement
                tail_angle = np.arctan2(-vel[1], -vel[0])
                tail_x = x + int(fish_size * 0.8 * np.cos(tail_angle))
                tail_y = y + int(fish_size * 0.8 * np.sin(tail_angle))
                cv2.line(frame, (x, y), (tail_x, tail_y), fish_color, 3)
                
        # Add feeding indicator
        if self.system_state == "FEEDING":
            cv2.putText(frame, "FEEDING", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                       
        # Add system info overlay
        info_y = self.frame_height - 80
        cv2.putText(frame, f"H: {self.h_value:.3f}", (10, info_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"PWM: {self.pwm_output:.1f}%", (10, info_y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"State: {self.system_state}", (10, info_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                   
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (self.frame_width - 100, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                   
        self.current_frame = frame
        
    def get_current_state(self):
        """Get current system state"""
        return {
            'h_value': self.h_value,
            'pwm_output': self.pwm_output,
            'features': self.features.copy(),
            'state': self.system_state,
            'fish_count': len(self.fish_positions),
            'feeding_activity': self.feeding_activity,
            'timestamp': time.time()
        }
        
    def get_camera_frame(self):
        """Get current camera frame"""
        return self.current_frame.copy() if self.current_frame is not None else None
        
    def set_parameters(self, h_hi=None, h_lo=None, kp=None, ki=None):
        """Set control parameters"""
        if h_hi is not None:
            self.h_hi = h_hi
            print(f"H_hi set to {h_hi}")
            
        if h_lo is not None:
            self.h_lo = h_lo
            print(f"H_lo set to {h_lo}")
            
        if kp is not None:
            self.kp = kp
            print(f"Kp set to {kp}")
            
        if ki is not None:
            self.ki = ki
            print(f"Ki set to {ki}")
            
    def manual_feed(self):
        """Trigger manual feeding"""
        self.feeding_activity = min(1.0, self.feeding_activity + 0.8)
        self.system_state = "FEEDING"
        self.last_state_change = time.time()
        print("Manual feeding triggered")
        
    def stop_simulation(self):
        """Stop simulation"""
        self.simulation_running = False
        print("Simulation stopped")
        
    def __del__(self):
        """Cleanup"""
        self.stop_simulation()


# Test function
def test_simulator():
    """Test the enhanced simulator"""
    print("Testing Enhanced System Simulator...")
    
    simulator = EnhancedSystemSimulator()
    
    # Run for a few seconds
    start_time = time.time()
    while time.time() - start_time < 5:
        state = simulator.get_current_state()
        frame = simulator.get_camera_frame()
        
        print(f"H: {state['h_value']:.3f}, PWM: {state['pwm_output']:.1f}%, "
              f"State: {state['state']}, Fish: {state['fish_count']}")
        
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
            
        time.sleep(1)
        
    simulator.stop_simulation()
    print("Test completed")


if __name__ == "__main__":
    test_simulator()
