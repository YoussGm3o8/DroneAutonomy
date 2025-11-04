"""
DLL Setup for Windows OpenCV and GStreamer

This module MUST be imported before any OpenCV imports.
It configures the DLL search paths for:
- Custom OpenCV build (C:\\opencv\\build\\bin\\Release)
- GStreamer libraries (C:\\gstreamer\\1.0\\msvc_x86_64\\bin)
"""

import os
import sys

def setup_opencv_gstreamer_dlls():
    """
    Configure OpenCV and GStreamer DLL paths for Windows.
    
    Call this function BEFORE importing cv2 or any module that imports cv2.
    """
    if sys.platform != 'win32':
        return  # Only needed on Windows

    print("--- Configuring DLL Paths for Windows ---")
    
    # Define paths
    opencv_bin = r"C:\opencv\build\bin\Release"
    gstreamer_bin = r"C:\gstreamer\1.0\msvc_x86_64\bin"
    gstreamer_lib = r"C:\gstreamer\1.0\msvc_x86_64\lib\gstreamer-1.0"
    
    # 1. Set GStreamer environment variables
    if os.path.exists(gstreamer_lib):
        os.environ['GST_PLUGIN_PATH'] = gstreamer_lib
        print(f"✓ Set GST_PLUGIN_PATH: {gstreamer_lib}")
    
    # 2. Add directories to system PATH for this process
    current_path = os.environ.get('PATH', '')
    new_paths = []
    if os.path.exists(opencv_bin) and opencv_bin not in current_path:
        new_paths.append(opencv_bin)
    if os.path.exists(gstreamer_bin) and gstreamer_bin not in current_path:
        new_paths.append(gstreamer_bin)
        
    if new_paths:
        os.environ['PATH'] = ';'.join(new_paths) + ';' + current_path
        print(f"✓ Added to process PATH: {', '.join(new_paths)}")

    # 3. Use os.add_dll_directory (Python 3.8+), the modern way
    if hasattr(os, 'add_dll_directory'):
        if os.path.exists(opencv_bin):
            try:
                os.add_dll_directory(opencv_bin)
                print(f"✓ Added OpenCV DLL directory: {opencv_bin}")
            except Exception as e:
                print(f"⚠ Warning: Could not add OpenCV DLL directory: {e}")
                
        if os.path.exists(gstreamer_bin):
            try:
                os.add_dll_directory(gstreamer_bin)
                print(f"✓ Added GStreamer DLL directory: {gstreamer_bin}")
            except Exception as e:
                print(f"⚠ Warning: Could not add GStreamer DLL directory: {e}")
    else:
        print("⚠ Warning: os.add_dll_directory not available (Python < 3.8). Relying on PATH.")
    
    print("-----------------------------------------")

# This function is now called from drone_autonomy/__init__.py
