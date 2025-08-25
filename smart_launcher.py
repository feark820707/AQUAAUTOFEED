#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Launcher for Aqua Feeder GUI
Automatically selects the best GUI version based on system capabilities
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

def check_gui_capabilities():
    """Check system capabilities for GUI features"""
    capabilities = {
        'tkinter': False,
        'matplotlib': False,
        'numpy': False,
        'scrollable': False
    }
    
    # Check tkinter
    try:
        import tkinter
        capabilities['tkinter'] = True
    except ImportError:
        return capabilities
        
    # Check matplotlib
    try:
        import matplotlib
        capabilities['matplotlib'] = True
    except ImportError:
        pass
        
    # Check numpy
    try:
        import numpy
        capabilities['numpy'] = True
    except ImportError:
        pass
        
    # Check scrollable capability (tkinter.ttk)
    try:
        from tkinter import ttk
        capabilities['scrollable'] = True
    except ImportError:
        pass
        
    return capabilities

def show_gui_selector():
    """Show GUI version selector"""
    root = tk.Tk()
    root.title("Aqua Feeder GUI Launcher")
    root.geometry("500x400")
    root.resizable(False, False)
    
    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = tk.Label(main_frame, text="Smart Aqua Feeder Control System", 
                          font=('Arial', 16, 'bold'))
    title_label.pack(pady=(0, 20))
    
    # Capabilities check
    caps = check_gui_capabilities()
    
    # Status display
    status_frame = tk.LabelFrame(main_frame, text="System Capabilities", padx=10, pady=10)
    status_frame.pack(fill=tk.X, pady=(0, 20))
    
    status_items = [
        ("Tkinter GUI Support", caps['tkinter']),
        ("Advanced Charts (Matplotlib)", caps['matplotlib']),
        ("Data Processing (NumPy)", caps['numpy']),
        ("Scrollable Interface", caps['scrollable'])
    ]
    
    for i, (label, status) in enumerate(status_items):
        status_text = "✓ Available" if status else "✗ Missing"
        color = "green" if status else "red"
        
        item_frame = tk.Frame(status_frame)
        item_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(item_frame, text=label).pack(side=tk.LEFT)
        tk.Label(item_frame, text=status_text, fg=color, font=('Arial', 9, 'bold')).pack(side=tk.RIGHT)
    
    # GUI version selection
    version_frame = tk.LabelFrame(main_frame, text="Available GUI Versions", padx=10, pady=10)
    version_frame.pack(fill=tk.X, pady=(0, 20))
    
    selected_gui = tk.StringVar(value="auto")
    
    gui_options = []
    
    if caps['scrollable'] and caps['matplotlib'] and caps['numpy']:
        gui_options.append(("standalone", "Advanced GUI (Standalone)", 
                          "Complete feature set with scrollable interface\n" +
                          "18+ parameters, real-time charts, auto-tuning"))
    
    if caps['tkinter'] and caps['matplotlib']:
        gui_options.append(("enhanced", "Enhanced GUI", 
                          "Camera display with ASCII-safe output\n" +
                          "Solves Chinese encoding issues"))
    
    if caps['tkinter']:
        gui_options.append(("basic", "Basic GUI", 
                          "Simple interface with core functionality\n" +
                          "Minimal system requirements"))
    
    gui_options.append(("auto", "Auto-Select Best Version", 
                       "Automatically choose the most advanced available version"))
    
    for value, label, description in gui_options:
        radio = tk.Radiobutton(version_frame, text=label, variable=selected_gui, 
                              value=value, font=('Arial', 10, 'bold'))
        radio.pack(anchor=tk.W, pady=2)
        
        desc_label = tk.Label(version_frame, text=description, 
                             font=('Arial', 9), fg='gray', wraplength=450)
        desc_label.pack(anchor=tk.W, padx=(20, 0), pady=(0, 10))
    
    # Recommendation
    if caps['scrollable'] and caps['matplotlib'] and caps['numpy']:
        recommended = "standalone"
        rec_text = "Recommended: Advanced GUI (All features available)"
    elif caps['matplotlib']:
        recommended = "enhanced"
        rec_text = "Recommended: Enhanced GUI (Good compatibility)"
    else:
        recommended = "basic"
        rec_text = "Recommended: Basic GUI (Basic functionality)"
        
    rec_label = tk.Label(main_frame, text=rec_text, 
                        font=('Arial', 10, 'bold'), fg='blue')
    rec_label.pack(pady=(0, 20))
    
    # Buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X)
    
    def launch_selected():
        choice = selected_gui.get()
        if choice == "auto":
            choice = recommended
            
        root.destroy()
        launch_gui(choice)
    
    def exit_app():
        root.destroy()
        sys.exit(0)
    
    tk.Button(button_frame, text="Launch Selected GUI", command=launch_selected,
             font=('Arial', 12, 'bold'), bg='lightgreen').pack(side=tk.LEFT, padx=(0, 10))
    
    tk.Button(button_frame, text="Exit", command=exit_app,
             font=('Arial', 12)).pack(side=tk.RIGHT)
    
    # Set default selection to recommended
    selected_gui.set(recommended)
    
    root.mainloop()

def launch_gui(gui_type):
    """Launch specific GUI version"""
    try:
        if gui_type == "standalone":
            print("Launching Standalone Advanced GUI...")
            from gui.standalone_advanced_gui import StandaloneAdvancedGUI
            app = StandaloneAdvancedGUI()
            app.run()
            
        elif gui_type == "enhanced":
            print("Launching Enhanced GUI...")
            from gui.enhanced_gui import EnhancedAquaFeederGUI
            app = EnhancedAquaFeederGUI()
            app.run()
            
        elif gui_type == "basic":
            print("Launching Basic GUI...")
            # Try to import basic GUI if it exists
            try:
                from gui.basic_gui import BasicAquaFeederGUI
                app = BasicAquaFeederGUI()
                app.run()
            except ImportError:
                print("Basic GUI not found, creating minimal GUI...")
                create_minimal_gui()
                
        else:
            raise ValueError(f"Unknown GUI type: {gui_type}")
            
    except Exception as e:
        error_msg = f"Failed to launch {gui_type} GUI: {str(e)}"
        print(error_msg)
        
        # Show error dialog
        root = tk.Tk()
        root.withdraw()
        
        result = messagebox.askyesno("GUI Launch Error", 
                                   f"{error_msg}\n\nWould you like to try a different GUI version?")
        
        if result:
            root.destroy()
            show_gui_selector()
        else:
            sys.exit(1)

def create_minimal_gui():
    """Create minimal GUI as fallback"""
    root = tk.Tk()
    root.title("Minimal Aqua Feeder Control")
    root.geometry("400x300")
    
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(frame, text="Minimal Aqua Feeder Control", 
            font=('Arial', 14, 'bold')).pack(pady=(0, 20))
    
    tk.Label(frame, text="System Status: Ready").pack(pady=5)
    tk.Label(frame, text="Mode: Simulation").pack(pady=5)
    
    tk.Button(frame, text="Start System", bg='lightgreen').pack(pady=10)
    tk.Button(frame, text="Stop System").pack(pady=5)
    tk.Button(frame, text="Emergency Stop", bg='red', fg='white').pack(pady=5)
    
    tk.Label(frame, text="This is a minimal fallback interface.\n" +
                        "For full features, install missing dependencies.",
            wraplength=350, justify=tk.CENTER).pack(pady=(20, 0))
    
    root.mainloop()

def main():
    """Main entry point"""
    print("Aqua Feeder Smart Launcher")
    print("Checking system capabilities...")
    
    # Check if running in console mode
    if len(sys.argv) > 1:
        gui_type = sys.argv[1].lower()
        if gui_type in ['standalone', 'enhanced', 'basic']:
            launch_gui(gui_type)
            return
        elif gui_type in ['-h', '--help']:
            print("\nUsage:")
            print("  python smart_launcher.py [gui_type]")
            print("\nGUI Types:")
            print("  standalone  - Advanced GUI with all features")
            print("  enhanced    - Enhanced GUI with camera display")
            print("  basic       - Basic GUI with core features")
            print("  (no args)   - Show GUI selector")
            return
            
    # Show GUI selector
    show_gui_selector()

if __name__ == "__main__":
    main()
