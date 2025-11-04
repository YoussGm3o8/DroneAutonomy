"""
DLL Setup for Windows OpenCV and GStreamer

This module MUST be imported before any OpenCV imports.
It configures the DLL search paths for:
- Custom OpenCV build (C:\\opencv\\build\\bin\\Release)
- GStreamer libraries (C:\\gstreamer\\1.0\\msvc_x86_64\\bin)
"""

import os
import sys


def setup_opencv_dlls():
    """
    Configure OpenCV and GStreamer DLL paths for Windows
    
    Call this function BEFORE importing cv2 or any module that imports cv2.
    """
    if sys.platform != 'win32':
        return  # Only needed on Windows
        
    opencv_bin = r"C:\opencv\build\bin\Release"
    gstreamer_bin = r"C:\gstreamer\1.0\msvc_x86_64\bin"
    
    # Add to PATH environment variable
    current_path = os.environ.get('PATH', '')
    os.environ['PATH'] = f"{opencv_bin};{gstreamer_bin};{current_path}"
    
    # Add to DLL search directories (Python 3.8+)
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
        print("⚠ Warning: os.add_dll_directory not available (Python < 3.8)")


# Auto-setup on import
setup_opencv_dlls()
