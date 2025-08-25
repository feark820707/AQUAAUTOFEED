#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Enhanced GUI Test
ASCII safe output and basic camera simulation
"""

import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from gui.enhanced_gui import EnhancedAquaFeederGUI
    
    print("Starting Enhanced Aqua Feeder GUI...")
    print("Features:")
    print("- ASCII safe output (no Chinese characters)")
    print("- Camera display simulation")
    print("- Real-time data monitoring")
    print("- Parameter adjustment")
    
    app = EnhancedAquaFeederGUI()
    app.run()
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying basic fallback...")
    
    try:
        from gui.main_gui import AquaFeederGUI
        print("Starting basic GUI...")
        app = AquaFeederGUI()
        app.root.mainloop()
    except Exception as e2:
        print(f"Basic GUI error: {e2}")
        
except Exception as e:
    print(f"Error: {e}")
    input("Press Enter to exit...")
    
print("GUI application closed.")
