"""
Quick profiling script to identify FPS bottlenecks
"""
import sys
import os
import time
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.detection.target_detector import TargetDetector

# Create a test frame
frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

print("=" * 80)
print("Performance Profiling - Identifying Bottlenecks")
print("=" * 80)
print(f"Test frame: {frame.shape}")
print()

# Test YOLO
print("Testing YOLO Detection...")
yolo_config = {
    'yolo_model': 'yolov8n.pt',
    'device': 'cuda',
    'confidence_threshold': 0.5,
    'nms_threshold': 0.4,
    'imgsz': 640
}
yolo = YOLODetector(yolo_config)
yolo.load_model()

times = []
for i in range(10):
    start = time.time()
    detections, det_time = yolo.detect(frame)
    elapsed = time.time() - start
    times.append(elapsed * 1000)
    print(f"  Run {i+1}: {elapsed*1000:.1f}ms ({len(detections)} detections)")

print(f"YOLO Average: {np.mean(times):.1f}ms ± {np.std(times):.1f}ms")
print()

# Test YOLO with smaller input
print("Testing YOLO with imgsz=416...")
yolo_config['imgsz'] = 416
yolo_small = YOLODetector(yolo_config)
yolo_small.load_model()

times = []
for i in range(10):
    start = time.time()
    detections, det_time = yolo_small.detect(frame)
    elapsed = time.time() - start
    times.append(elapsed * 1000)
    print(f"  Run {i+1}: {elapsed*1000:.1f}ms ({len(detections)} detections)")

print(f"YOLO-416 Average: {np.mean(times):.1f}ms ± {np.std(times):.1f}ms")
print()

# Test Depth
print("Testing Depth Estimation...")
depth_config = {
    'model': 'MiDaS_small',
    'device': 'cuda',
    'input_size': [384, 384]
}
depth = DepthEstimator(depth_config)
depth.load_model()

times = []
for i in range(10):
    start = time.time()
    depth_map, depth_time = depth.estimate_depth(frame)
    elapsed = time.time() - start
    times.append(elapsed * 1000)
    print(f"  Run {i+1}: {elapsed*1000:.1f}ms")

print(f"Depth Average: {np.mean(times):.1f}ms ± {np.std(times):.1f}ms")
print()

# Test Target Detection
print("Testing Target Detection...")
target_config = {
    'hsv_lower': [0, 100, 100],
    'hsv_upper': [10, 255, 255],
    'min_radius': 10,
    'max_radius': 200,
    'circle_threshold': 0.7
}
target = TargetDetector(target_config)

times = []
for i in range(10):
    start = time.time()
    targets, target_time = target.detect(frame)
    elapsed = time.time() - start
    times.append(elapsed * 1000)
    print(f"  Run {i+1}: {elapsed*1000:.1f}ms ({len(targets)} targets)")

print(f"Target Average: {np.mean(times):.1f}ms ± {np.std(times):.1f}ms")
print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("Component Timing (average):")
print(f"  YOLO (640):  ~{np.mean([t for t in times]):.0f}ms")
print(f"  YOLO (416):  ~{np.mean([t for t in times]):.0f}ms")  
print(f"  Depth:       ~{np.mean([t for t in times]):.0f}ms")
print(f"  Target:      ~{np.mean([t for t in times]):.0f}ms")
print()
print("Expected FPS:")
print(f"  Full pipeline (640 YOLO + Depth): {1000/(np.mean([t for t in times])*4):.1f} FPS")
print(f"  Fast mode (640 YOLO only):        {1000/(np.mean([t for t in times])*2):.1f} FPS")
print(f"  Fast mode (416 YOLO only):        {1000/(np.mean([t for t in times])*2):.1f} FPS")
print("=" * 80)
