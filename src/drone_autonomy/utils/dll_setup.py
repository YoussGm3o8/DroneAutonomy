"""
DLL Setup for OpenCV with GStreamer support.

This module must be imported before cv2 to ensure proper DLL loading.
"""
import os
import sys


def setup_opencv_gstreamer_dlls():
    """
    Add OpenCV and GStreamer directories to DLL search path.
    
    This function should be called before importing cv2 to ensure
    that OpenCV can find the GStreamer DLLs it depends on.
    """
    opencv_bin = "C:\\opencv\\build\\bin\\Release"
    gstreamer_bin = "C:\\gstreamer\\1.0\\msvc_x86_64\\bin"
    gstreamer_lib = "C:\\gstreamer\\1.0\\msvc_x86_64\\lib\\gstreamer-1.0"
    
    # Set GStreamer environment variables BEFORE any OpenCV/GStreamer usage
    if os.path.exists(gstreamer_lib):
        os.environ['GST_PLUGIN_PATH'] = gstreamer_lib
        os.environ['GST_PLUGIN_SYSTEM_PATH'] = gstreamer_lib
        print(f"Set GST_PLUGIN_PATH: {gstreamer_lib}")
    
    # Add directories if they exist
    if os.path.exists(opencv_bin):
        os.add_dll_directory(opencv_bin)
        print(f"Added OpenCV DLL directory: {opencv_bin}")
    else:
        print(f"Warning: OpenCV directory not found: {opencv_bin}")
    
    if os.path.exists(gstreamer_bin):
        os.add_dll_directory(gstreamer_bin)
        print(f"Added GStreamer DLL directory: {gstreamer_bin}")
    else:
        print(f"Warning: GStreamer directory not found: {gstreamer_bin}")


# Automatically setup DLLs when this module is imported
setup_opencv_gstreamer_dlls()