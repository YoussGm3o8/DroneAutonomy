"""Diagnose GStreamer OpenCV issues"""
import cv2
import os
import sys

# Enable GStreamer debug logging
os.environ['GST_DEBUG'] = '3'  # 0=none, 5=debug, 9=all

print("="*80)
print("GStreamer + OpenCV Diagnostics")
print("="*80)

# Check OpenCV build info
print("\n1. OpenCV Build Information:")
print("-" * 40)
build_info = cv2.getBuildInformation()
for line in build_info.split('\n'):
    if 'GStreamer' in line or 'Video I/O' in line:
        print(line)

# Test simple pipeline first
print("\n2. Testing simple pipeline (videotestsrc):")
print("-" * 40)
test_pipeline = "videotestsrc ! videoconvert ! video/x-raw,format=BGR ! appsink"
cap = cv2.VideoCapture(test_pipeline, cv2.CAP_GSTREAMER)
if cap.isOpened():
    print("OK Simple test pipeline works!")
    ret, frame = cap.read()
    if ret:
        print(f"OK Frame read: {frame.shape}")
    cap.release()
else:
    print("FAIL Simple test pipeline failed - OpenCV GStreamer integration broken")
    sys.exit(1)

# Test file playback (if you have a test video)
print("\n3. Testing RTSP stream:")
print("-" * 40)
rtsp_url = "rtsp://192.168.1.231:8554/1"
pipeline = f"rtspsrc location={rtsp_url} latency=0 ! decodebin ! videoconvert ! appsink"
print(f"Pipeline: {pipeline}")

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
print(f"isOpened(): {cap.isOpened()}")

if cap.isOpened():
    print("✓ RTSP pipeline opened!")
    for i in range(5):
        ret, frame = cap.read()
        if ret:
            print(f"  Frame {i+1} received: {frame.shape}")
        else:
            print(f"  Frame {i+1} failed")
            break
    cap.release()
else:
    print("✗ RTSP pipeline failed to open")
    
print("\n4. Alternative: Try VLC backend")
print("-" * 40)
print("Testing if regular URL works (OpenCV may use FFmpeg):")
cap = cv2.VideoCapture(rtsp_url)
if cap.isOpened():
    print("✓ Direct RTSP URL works with default backend!")
    ret, frame = cap.read()
    if ret:
        print(f"✓ Frame received: {frame.shape}")
        print("\nSOLUTION: Use direct URL instead of GStreamer pipeline")
    cap.release()
else:
    print("✗ Direct RTSP URL also failed")

print("\n" + "="*80)
