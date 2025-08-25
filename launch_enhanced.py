#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Launcher for Aqua Feeder Control System
ASCII safe output and camera support
"""

import sys
import os
import subprocess
import threading
import time

def check_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        'tkinter',
        'matplotlib', 
        'numpy',
        'opencv-python',
        'Pillow',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            elif package == 'opencv-python':
                import cv2
            elif package == 'Pillow':
                import PIL
            else:
                __import__(package)
            print(f"✓ {package} - OK")
        except ImportError:
            print(f"✗ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nInstalling missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError:
                print(f"✗ Failed to install {package}")
                return False
    
    return True

def print_banner():
    """Print ASCII banner"""
    banner = """
    ======================================================
     Aqua Feeder Control System v1.0 Enhanced
    ======================================================
     Features:
     * ASCII Safe Output (No Chinese Characters)
     * Camera Display Support  
     * Real-time Data Monitoring
     * Parameter Adjustment Interface
     * Simulation and Hardware Modes
    ======================================================
    """
    print(banner)

def print_menu():
    """Print main menu"""
    menu = """
    Select an option:
    
    1. Start Enhanced GUI (Recommended)
    2. Start Original GUI  
    3. Configuration Editor
    4. Log Viewer
    5. System Test
    6. Exit
    
    Enter your choice (1-6): """
    
    return input(menu).strip()

def launch_enhanced_gui():
    """Launch enhanced GUI with camera support"""
    print("\nStarting Enhanced GUI...")
    print("Features: Camera display, ASCII output, real-time monitoring")
    
    try:
        # Add current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # Import and run enhanced GUI
        from gui.enhanced_gui import EnhancedAquaFeederGUI
        
        app = EnhancedAquaFeederGUI()
        app.run()
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Falling back to basic GUI...")
        launch_basic_gui()
    except Exception as e:
        print(f"Error starting enhanced GUI: {e}")
        input("Press Enter to continue...")

def launch_basic_gui():
    """Launch basic GUI"""
    print("\nStarting Basic GUI...")
    
    try:
        # Add current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from gui.main_gui import AquaFeederGUI
        
        app = AquaFeederGUI()
        app.run()
        
    except Exception as e:
        print(f"Error starting basic GUI: {e}")
        input("Press Enter to continue...")

def launch_config_editor():
    """Launch configuration editor"""
    print("\nStarting Configuration Editor...")
    
    try:
        from gui.config_editor import ConfigEditor
        import tkinter as tk
        
        root = tk.Tk()
        app = ConfigEditor(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting config editor: {e}")
        input("Press Enter to continue...")

def launch_log_viewer():
    """Launch log viewer"""
    print("\nStarting Log Viewer...")
    
    try:
        from gui.log_viewer import LogViewer
        import tkinter as tk
        
        root = tk.Tk()
        app = LogViewer(root)
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting log viewer: {e}")
        input("Press Enter to continue...")

def run_system_test():
    """Run system test"""
    print("\nRunning System Test...")
    
    try:
        # Import test module
        test_script = os.path.join(os.path.dirname(__file__), 'test_gui.py')
        if os.path.exists(test_script):
            subprocess.run([sys.executable, test_script])
        else:
            print("Test script not found. Running basic component test...")
            
            # Basic component test
            print("Testing components...")
            
            components = {
                'tkinter': lambda: __import__('tkinter'),
                'matplotlib': lambda: __import__('matplotlib'),
                'numpy': lambda: __import__('numpy'),
                'cv2': lambda: __import__('cv2'),
                'PIL': lambda: __import__('PIL')
            }
            
            for name, test_func in components.items():
                try:
                    test_func()
                    print(f"✓ {name} - OK")
                except ImportError:
                    print(f"✗ {name} - Missing")
            
            print("\nComponent test completed.")
            
    except Exception as e:
        print(f"Error running system test: {e}")
    
    input("Press Enter to continue...")

def main():
    """Main application entry point"""
    # Set up ASCII encoding for Windows
    if sys.platform.startswith('win'):
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'C')
        except:
            pass
    
    print_banner()
    
    # Check dependencies first
    print("Checking dependencies...")
    if not check_dependencies():
        print("Failed to install required dependencies.")
        input("Press Enter to exit...")
        return
    
    print("All dependencies are available.")
    
    while True:
        try:
            choice = print_menu()
            
            if choice == '1':
                launch_enhanced_gui()
            elif choice == '2':
                launch_basic_gui()
            elif choice == '3':
                launch_config_editor()
            elif choice == '4':
                launch_log_viewer()
            elif choice == '5':
                run_system_test()
            elif choice == '6':
                print("Exiting... Thank you for using Aqua Feeder Control System!")
                break
            else:
                print("Invalid choice. Please enter 1-6.")
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
