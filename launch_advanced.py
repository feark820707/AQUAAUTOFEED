#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced GUI Launcher
Comprehensive parameter management and scrollable interface
"""

import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("=" * 60)
print("Advanced Aqua Feeder Control System v2.0")
print("=" * 60)
print("Features:")
print("✓ Scrollable interface - No space limitations")
print("✓ Comprehensive parameter management")
print("✓ Real-time and simulation modes")
print("✓ Auto-tuning capabilities")
print("✓ Enhanced data visualization")
print("✓ Configuration save/load")
print("=" * 60)

try:
    # Import and start advanced GUI
    from gui.advanced_gui import AdvancedAquaFeederGUI
    
    print("Initializing advanced GUI system...")
    app = AdvancedAquaFeederGUI()
    print("Advanced GUI ready - starting application...")
    app.run()
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Falling back to enhanced GUI...")
    
    try:
        from gui.enhanced_gui import EnhancedAquaFeederGUI
        print("Starting enhanced GUI fallback...")
        app = EnhancedAquaFeederGUI()
        app.run()
    except ImportError:
        print("Enhanced GUI not available, trying basic GUI...")
        try:
            from gui.main_gui import AquaFeederGUI
            print("Starting basic GUI...")
            app = AquaFeederGUI()
            app.root.mainloop()
        except Exception as e:
            print(f"All GUI options failed: {e}")
            input("Press Enter to exit...")
            
except Exception as e:
    print(f"Error starting advanced GUI: {e}")
    print("This might be due to missing dependencies or system limitations.")
    
    # Try to show helpful error information
    print("\nTroubleshooting:")
    print("1. Ensure all dependencies are installed: pip install -r requirements.txt")
    print("2. Check Python version (3.8+ recommended)")
    print("3. Verify tkinter is properly installed")
    print("4. Try running: python test_enhanced_gui.py")
    
    input("Press Enter to exit...")

print("Advanced GUI application closed.")
