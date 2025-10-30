"""
Test Full Pipeline Performance with Depth Anything V2

This script tests the complete processing pipeline including:
- Target detection (YOLO)
- Depth estimation (Depth Anything V2)
- Decision fusion

Usage:
    python examples/test_pipeline_performance.py [--frames 100]
"""

import sys
import time
import argparse
import numpy as np
import cv2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.utils.dll_setup import setup_opencv_gstreamer_dlls
setup_opencv_gstreamer_dlls()

from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.depth.depth_estimator import DepthEstimator


def generate_test_frame(width: int = 1920, height: int = 1080):
    """Generate synthetic test frame"""
    # Create random background
    frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # Add some "target-like" circles in random locations
    num_targets = np.random.randint(0, 3)
    for _ in range(num_targets):
        cx = np.random.randint(100, width - 100)
        cy = np.random.randint(100, height - 100)
        radius = np.random.randint(20, 60)
        color = (int(np.random.randint(0, 100)), 
                int(np.random.randint(0, 100)), 
                int(np.random.randint(150, 255)))  # Reddish
        cv2.circle(frame, (cx, cy), radius, color, -1)
    
    return frame


def test_pipeline_performance(num_frames: int = 100):
    """Test complete pipeline performance"""
    print("=" * 80)
    print("Full Pipeline Performance Test with Depth Anything V2")
    print("=" * 80)
    print()
    
    # Initialize components
    print("Initializing components...")
    print("  1/3 Loading YOLO detector...")
    yolo_config = {
        'yolo_model': 'yolov8n.pt',
        'confidence_threshold': 0.5,
        'device': 'cuda',
        'imgsz': 640,
        'use_tensorrt': False
    }
    yolo = YOLODetector(yolo_config)
    if not yolo.load_model():
        print("❌ Failed to load YOLO model!")
        return
    
    print("  2/3 Loading Depth Anything V2...")
    depth_config = {
        'model': 'depth_anything_v2_vits',
        'device': 'cuda',
        'input_size': [518, 518],
        'output_scale': 1.0
    }
    depth = DepthEstimator(depth_config)
    if not depth.load_model():
        print("❌ Failed to load depth model!")
        return
    
    print("  3/3 Decision Layer not needed for performance test")
    
    print("✓ All components loaded\n")
    
    # Generate test frame
    print("Generating test frames...")
    test_frame = generate_test_frame(1920, 1080)
    print(f"  Frame size: {test_frame.shape[1]}x{test_frame.shape[0]}\n")
    
    # Warmup
    print("Running warmup...")
    for _ in range(3):
        _ = yolo.detect(test_frame)
        _, _ = depth.estimate_depth(test_frame)
    print("✓ Warmup complete\n")
    
    # Performance test
    print(f"Running {num_frames} frames through complete pipeline...\n")
    
    times = {
        'detection': [],
        'depth': [],
        'fusion': [],
        'total': []
    }
    
    for i in range(num_frames):
        # Generate new random frame each time
        frame = generate_test_frame(1920, 1080)
        
        frame_start = time.time()
        
        # Detection
        det_start = time.time()
        detections = yolo.detect(frame)
        det_time = time.time() - det_start
        
        # Depth estimation
        depth_start = time.time()
        depth_map, _ = depth.estimate_depth(frame)
        depth_time = time.time() - depth_start
        
        # Skip fusion for this performance test
        fusion_time = 0
        
        total_time = time.time() - frame_start
        
        # Record times
        times['detection'].append(det_time * 1000)
        times['depth'].append(depth_time * 1000)
        times['fusion'].append(fusion_time * 1000)
        times['total'].append(total_time * 1000)
        
        if (i + 1) % 10 == 0:
            current_fps = 1000 / np.mean(times['total'][-10:])
            print(f"  Frame {i+1}/{num_frames}: "
                  f"Det={det_time*1000:.1f}ms, "
                  f"Depth={depth_time*1000:.1f}ms, "
                  f"Total={total_time*1000:.1f}ms, "
                  f"FPS={current_fps:.1f}")
    
    # Calculate statistics
    print("\n" + "=" * 80)
    print("PERFORMANCE RESULTS")
    print("=" * 80)
    print()
    
    for component, component_times in times.items():
        avg = np.mean(component_times)
        std = np.std(component_times)
        min_t = np.min(component_times)
        max_t = np.max(component_times)
        
        if component == 'total':
            fps = 1000 / avg
            print(f"{component.upper()}:")
            print(f"  Average: {avg:.2f}ms (±{std:.2f}ms)")
            print(f"  Range: {min_t:.2f}ms - {max_t:.2f}ms")
            print(f"  FPS: {fps:.2f}")
        else:
            percent = (avg / np.mean(times['total'])) * 100
            print(f"{component.upper()}:")
            print(f"  Average: {avg:.2f}ms (±{std:.2f}ms) [{percent:.1f}% of total]")
            print(f"  Range: {min_t:.2f}ms - {max_t:.2f}ms")
        print()
    
    # Bottleneck analysis
    print("=" * 80)
    print("BOTTLENECK ANALYSIS")
    print("=" * 80)
    print()
    
    avg_times = {k: np.mean(v) for k, v in times.items() if k != 'total'}
    sorted_components = sorted(avg_times.items(), key=lambda x: x[1], reverse=True)
    
    for i, (component, avg_time) in enumerate(sorted_components, 1):
        percent = (avg_time / np.mean(times['total'])) * 100
        bars = "█" * int(percent / 2)
        print(f"{i}. {component.upper()}: {bars} {percent:.1f}%")
    
    print()
    print("=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test full pipeline performance')
    parser.add_argument('--frames', type=int, default=50,
                       help='Number of frames to test (default: 50)')
    
    args = parser.parse_args()
    
    test_pipeline_performance(args.frames)
